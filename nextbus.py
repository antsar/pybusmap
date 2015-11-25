from requests import get, ConnectionError
from lxml import etree
import json
import time
from datetime import datetime, timedelta
from models import Agency, ApiCall, Direction, Prediction, Region, Route, Stop, VehicleLocation
from app import app, db
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from lock import Lock
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
from urllib.parse import urlencode

class Nextbus():
    """
    The NextBus data source
    NextBus Inc. - www.nextbus.com
    API Format: XML
    API Doc: https://www.nextbus.com/xmlFeedDocs/NextBusXMLFeed.pdf
    """

    api_url = "http://webservices.nextbus.com/service/publicXMLFeed"

    api_limits = {                          # As per Nextbus API doc Rev. 1.22, April 4 2013.
        'max_bytes': 2 * 1024**2,           # 2MB
        'max_bytes_timeframe_seconds': 20,  # per 20 seconds
        'routeconfig_max_routes': 100,      # here for reference only, enforced implicitly
        'predictions_max_stops': 150,       # max stops per predictionsForMultiStops
        'max_predictions_per_stop': 5,      # here for reference only; this is just informational
        'max_location_age': 5 * 60,         # max timespan for vehicleLocations
        'max_concurrent_requests': 50,
    }

    def _xml_to_tree(xml_string):
        """
        Convert an XML string to a navigable tree.
        """
        try:
            xmlroot = etree.fromstring(xml_string)
        except:
            raise(NextbusException("Unparseable XML received.\n{0}".format(xml_string)))
        return etree.ElementTree(xmlroot)

    @classmethod
    def request(cls, params, tagName):
        """
        Perform an API request specified by params
        and return all elements called tagName (or None, for a failed request)
        """
        if cls.remaining_quota() <= 0:
            raise(NextbusQuotaException(
                "Over Quota ({0}MB per {1} seconds). Try again later."\
                .format(cls.api_limits['max_bytes']/1024**2,
                    cls.api_limits['max_bytes_timeframe_seconds'])))
        error = None
        response = None
        try:
            response = get(cls.api_url, params)
        except ConnectionError:
            pass
        if response and response.status_code == 200:
            tree = cls._xml_to_tree(response.content)
            error = tree.find('Error')
        # Log the request
        api_call = ApiCall(
            url = cls.api_url if response else None,
            params = params,
            size = response.headers['content-length']
                if (response and 'content-length' in response.headers) else 0,
            status = response.status_code if response else 0,
            error = error.text if error else None if response else "Connection Error",
            source = 'Nextbus'
        )
        db.session.add(api_call)
        # Handle API error
        if error:
            should_retry = error.get('shouldRetry')
            if should_retry == False:
                # This is a permanent error, so we are probably doing something wrong.
                raise(NextbusException("Fatal NextBus API error: ".format(error.text)))
        if not response or response.status_code != 200 or error:
            # Return empty response for network errors and temporary API errors
            return None, api_call
        else:
            return tree.findall(tagName), api_call

    @classmethod
    def async_request(cls, requests):
        """
        Perform API requests asynchrously.
        requests is a list of (params, tagName) tuples.
        """
        fs = FuturesSession(max_workers=cls.api_limits['max_concurrent_requests'])
        futures = []
        api_calls = []
        # Start parallel requests
        for (params, tagName) in requests:
            url = "{0}?{1}".format(cls.api_url,
                                  urlencode(params, doseq=True))
            futures.append((fs.get(url), params))
        # Handle results as they are available
        results = []
        for (f, params) in futures:
            # These are blocking, so will stop if one isnt available yet. Poop.
            error = None
            response = f.result()
            if response and response.status_code == 200:
                tree = cls._xml_to_tree(response.content)
                error = tree.find('Error')
            # Log the request
            api_call = ApiCall(
                url = cls.api_url,
                params = params,
                size = response.headers['content-length']
                    if (response and 'content-length' in response.headers) else None,
                status = response.status_code if response else None,
                error = error.text if error is not None else None if response else "Connection Error",
                source = 'Nextbus'
            )
            api_calls.append(api_call)
            # Handle API error
            if error is not None:
                should_retry = error.get('shouldRetry')
                if should_retry == False:
                    # This is a permanent error, so we are probably doing something wrong.
                    raise(NextbusException("Fatal NextBus API error: ".format(error.text)))
            if not response or response.status_code != 200 or error is not None:
                # Return empty response for network errors and temporary API errors
                results.append((None, api_call))
            else:
                results.append((tree.findall(tagName), api_call))
        for ac in api_calls:
            db.session.add(ac)
        db.session.commit()
        return results

    @classmethod
    def remaining_quota(cls):
        """
        Get count of bytes we are allowed to retrieve as per API rate limit.
        """
        delta = timedelta(seconds=cls.api_limits['max_bytes_timeframe_seconds'])
        bytes_allowed = cls.api_limits['max_bytes']
        time_begin = datetime.now() - delta
        bytes_used = db.session.query(
                        db.func.coalesce(
                            db.func.sum(ApiCall.size),
                            0)
                    ).filter(ApiCall.time >= time_begin).one()[0]
        # Return zero if we've gone over-quota (negative quota makes no sense)
        return max(bytes_allowed - bytes_used, 0)

    @classmethod
    def get_agencies(cls, truncate=True):
        """
        Get a list of agencies
        """
        with Lock("agencies"):
            request_params = {
                'command': 'agencyList',
            }
            agencies_xml, api_call = cls.request(request_params, 'agency')
            if not agencies_xml:
                return []
            db.session.begin()
            if truncate:
                db.session.query(Agency).delete()
            agencies = []
            for agency in agencies_xml:
                region = Region.get_or_create(db.session,
                    title=agency.get('regionTitle'))
                a = Agency.get_or_create(db.session,
                    tag = agency.get('tag'),
                    title = agency.get('title'),
                    short_title = agency.get('shortTitle'),
                    region = region,
                    api_call = api_call)
                agencies.append(a)
            db.session.commit()
            return agencies

    @classmethod
    def get_routes(cls, agency_tag, truncate=True):
        """
        Get the routes for an agency.
        There are two API commands: routeList and routeConfig.
        routeConfig is needed to get full details about a route,
        but can only show 100 routes at a time. So, use routeList
        to get a list, then batch the first 100 and piecemeal the rest.
        """
        with Lock("agencies", shared=True), Lock("routes"):
            def save_route(route_xml, api_call):
                def save_directions(route_xml, route_obj, api_call):
                    directions = route_xml.findall('direction')
                    for direction in directions:
                        d =  Direction.get_or_create(db.session,
                            tag = direction.get('tag'),
                            title = direction.get('title'),
                            name = direction.get('name'),
                            api_call = api_call)
                        route_obj.directions.append(d)
                def save_stops(route_xml, route_obj, api_call):
                    stops = route_xml.findall('stop')
                    for stop in stops:
                        s =  Stop.get_or_create(db.session,
                            tag = stop.get('tag'),
                            title = stop.get('title'),
                            lat = stop.get('lat'),
                            lon = stop.get('lon'),
                            stop_id = stop.get('stopId'),
                            api_call = api_call)
                        route_obj.stops.append(s)
                r = Route.get_or_create(db.session,
                    tag = route_xml.get('tag'),
                    title = route_xml.get('title'),
                    color = route_xml.get('color'),
                    opposite_color = route_xml.get('oppositeColor'),
                    lat_min = route_xml.get('latMin'),
                    lat_max = route_xml.get('latMax'),
                    lon_min = route_xml.get('lonMin'),
                    lon_max = route_xml.get('lonMax'),
                    agency_id = agency.id,
                    api_call = api_call)
                save_directions(route_xml, r, api_call)
                save_stops(route_xml, r, api_call)
                return r

            # Get list of routes
            request_params = {
                'command': 'routeList',
                'a': agency_tag
            }
            routelist_xml, routelist_api_call = cls.request(request_params, 'route')

            if not routelist_xml:
                return []

            db.session.begin()
            ### TODO: This transaction stays open too long! Can we shortedn it?
            agency = db.session.query(Agency).filter_by(tag=agency_tag).one()
            if truncate:
                db.session.query(Route).filter_by(agency_id=agency.id).delete()

            # Batch-import as many as Nextbus allows (100)
            request_params = {
                'command': 'routeConfig',
                'a': agency.tag,
            }
            rc_xml, rc_api_call = cls.request(request_params, 'route')

            routes = []
            for route in rc_xml:
                r = save_route(route, rc_api_call)
                routes.append(r)

            # Do the rest one-by-one
            requests = []
            for route in routelist_xml:
                route_tag = route.get('tag')
                if route_tag not in [r.tag for r in routes]:
                    request_params = {
                        'command': 'routeConfig',
                        'a': agency.tag,
                        'route': route_tag
                    }
                    requests.append((request_params, 'route'))
            responses = cls.async_request(requests)
            db.session.begin()
            for rc_xml, rc_api_call in responses:
                r = save_route(rc_xml[0], rc_api_call)
                routes.append(r)
            db.session.commit()
            return routes

    @classmethod
    def get_predictions(cls, routes, truncate=True):
        """
        Get vehicle arrival predictions
        request parameter 'stops' is actually a list of "route|stop" pairs
        """
        with Lock("agencies", shared=True), Lock("routes", shared=True):
            if not routes:
                return []
            db.session.begin()
            # Re-do this query inside the transaction, in case routes went poof in the meantime.
            # This is probably dumb but I don't have a cleaner solution in mind for now...
            # caveat: if routes were updated, get_predictions will silently fail (return nothing)
            routes = db.session.query(Route)\
                .filter(Route.id.in_([r.id for r in routes])).all()
            routes = {(r.agency.tag, r.tag): r for r in routes}
            if truncate:
                db.session.query(Prediction)\
                    .filter(
                        Prediction.route_id.in_(
                            [r.id for r in routes]
                        ))\
                    .delete(synchronize_session=False)
                db.session.expire_all()
            all_stops = {}
            for (a_tag, r_tag) in routes:
                route = routes[(a_tag, r_tag)]
                for s in route.stops:
                    if route.agency.tag not in all_stops:
                        all_stops[route.agency.tag] = []
                    all_stops[route.agency.tag].append("{0}|{1}".format(route.tag, s))
            requests = []
            predictions = []
            # Break this up by agency, since agency tag is a request param.
            for agency_tag in all_stops:
                # Further break the request into batches to comply with API limits
                stops_per_request = cls.api_limits['predictions_max_stops']
                batches = [all_stops[agency_tag][x:x+stops_per_request]
                    for x in range(0, len(all_stops[agency_tag]), stops_per_request)]
                for stops in batches:
                    request_params = {
                        'command': 'predictionsForMultiStops',
                        'a': agency_tag,
                        'stops': stops
                    }
                    requests.append((request_params, 'predictions'))
            responses = cls.async_request(requests)
            for prediction_sets, api_call in responses:
                if not prediction_sets:
                    continue
                agency_tag = api_call.params['a']
                for prediction_set in prediction_sets:
                    route_tag = prediction_set.get('routeTag')
                    route = routes[(agency_tag, route_tag)]
                    stop_tag = prediction_set.get('stopTag')
                    try:
                        stop = route.stops[stop_tag]
                    except KeyError:
                        raise(NextbusException("Non-existent stop '{0}' for agency '{1}' route '{2}'"\
                            .format(stop_tag, route.agency.tag, route.tag)))
                    for direction in prediction_set.findall('direction'):
                        xml_predictions = direction.findall('prediction')
                        for prediction in xml_predictions:
                            # Try to identify the Direction. Use "None" if Nextbus gave an invalid one (happens)
                            direction = next((d for d in route.directions if d.tag == prediction.get('dirTag')), None)
                            # Nextbus gives epoch with msecs; divide by 1k and convert
                            predicted_seconds = int(prediction.get('epochTime'))/1000
                            predicted_time = datetime.fromtimestamp(predicted_seconds)
                            # create the prediction
                            p_params = {'route_id': route.id,
                                'stop_id': stop.id,
                                'prediction': predicted_time,
                                'is_departure': prediction.get('isDeparture'),
                                'has_layover': prediction.get('affectedByLayover'),
                                'direction_id': direction.id if direction else None,
                                'vehicle': prediction.get('vehicle'),
                                'block': prediction.get('block'),
                                'api_call_id': api_call.id}
                            predictions.append(p_params)
            db.session.begin()
            db.engine.execute(Prediction.__table__.insert(), predictions)
            db.session.commit()
            return predictions

    @classmethod
    def get_vehicle_locations(cls, routes, truncate=True):
        """
        Get vehicle GPS locations
        """
        with Lock("agencies", shared=True), Lock("routes", shared=True):
            db.session.begin()
            # Re-do this query inside the transaction, in case routes went poof in the meantime.
            # This is probably dumb but I don't have a cleaner solution in mind for now...
            # caveat: if routes were updated, get_predictions will silently fail (return nothing)
            routes = db.session.query(Route)\
                .options(joinedload('directions'))\
                .filter(Route.id.in_([r.id for r in routes])).all()
            most_recent = db.session.query(VehicleLocation.route_id,
                            db.func.max(ApiCall.time))\
                    .join(ApiCall)\
                    .filter(
                        VehicleLocation.route_id.in_([r.id for r in routes]))\
                    .group_by(VehicleLocation.route_id).all()
            last_time = {}
            for route_id, mr_time in most_recent:
                last_time[route_id] = mr_time
            requests = []
            for route in routes:
                t = last_time[route.id].timestamp() if route.id in last_time else 0
                request_params = {
                    'command': 'vehicleLocations',
                    'a': route.agency.tag,
                    'r': route.tag,
                    't': int(t)
                }
                requests.append((request_params, 'vehicle'))
            responses = cls.async_request(requests)
            vehicle_locations = []
            for (vehicles, api_call) in responses:
                if not vehicles:
                    continue
                for vehicle in vehicles:
                    route = next((r for r in routes if r.tag == vehicle.get('routeTag')), None)
                    if route:
                        direction = next((d for d in route.directions if d.tag == vehicle.get('dirTag')), None)
                    else:
                        direction = None
                    # Convert age in seconds to a DateTime
                    age = timedelta(seconds=int(vehicle.get('secsSinceReport')))
                    time = datetime.now() - age
                    # Convert negative heading to None, as per API docs
                    heading = int(vehicle.get('heading'))
                    if heading < 0:
                        heading = None
                    # Save it all
                    vl = {'vehicle': vehicle.get('id'),
                        'route_id': route.id if route else None,
                        'direction_id': direction.id if direction else None,
                        'lat': vehicle.get('lat'),
                        'lon': vehicle.get('lon'),
                        'time': time,
                        'predictable': vehicle.get('predictable'),
                        'heading': heading,
                        'speed': float(vehicle.get('speedKmHr')),
                        'api_call_id': api_call.id}
                    vehicle_locations.append(vl)
            db.session.begin()
            db.engine.execute(VehicleLocation.__table__.insert(), vehicle_locations)
            db.session.commit()
            return vehicle_locations

    @classmethod
    def delete_stale_predictions(cls):
        """
        Delete predictions older than PREDICTIONS_MAX_AGE.
        """
        expire = datetime.now() - timedelta(seconds=app.config['PREDICTIONS_MAX_AGE'])
        delete = db.session.query(Prediction)\
                    .filter(Prediction.created < expire)\
                    .delete(synchronize_session=False)
        return delete

    @classmethod
    def delete_stale_vehicle_locations(cls):
        """
        Delete vehicle locations older than LOCATIONS_MAX_AGE.
        """
        expire = datetime.now() - timedelta(seconds=app.config['LOCATIONS_MAX_AGE'])
        delete = db.session.query(VehicleLocation)\
                    .filter(VehicleLocation.time < expire)\
                    .delete(synchronize_session=False)
        return delete

class NextbusException(Exception):
    """ General-purpose API error """
    pass

class NextbusQuotaException(Exception):
    """ API quota exceeded. """
    pass
