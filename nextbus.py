from requests import get, ConnectionError
from lxml import etree
import json
from datetime import datetime, timedelta
from models import Agency, ApiCall, Direction, Prediction, Region, Route, Stop
from app import db
from sqlalchemy.exc import IntegrityError

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
    }

    @classmethod
    def request(cls, params, tagName):
        """
        Perform an API request specified by params
        and return all elements called tagName (or None, for a failed request)
        """
        if cls.remaining_quota() <= 0:
            raise(NextbusQuotaException("Over Quota ({0}MB per {1} seconds). Try again later."\
                .format(cls.api_limits['max_bytes']/1024**2, cls.api_limits['max_bytes_timeframe_seconds'])))
        error = None
        response = None
        try:
            response = get(cls.api_url, params)
        except ConnectionError:
            pass
        if response and response.status_code == 200:
            xmlroot = etree.fromstring(response.content)
            tree = etree.ElementTree(xmlroot)
            error = tree.find('Error')
        # Log the request
        api_call = ApiCall(
            url = response.url if response else None,
            size = response.headers['content-length'] if (response and 'content-length' in response.headers) else 0,
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
            # Silently return empty response for network errors and non-permanent API errors
            return None, api_call
        else:
            return tree.findall(tagName), api_call

    @classmethod
    def remaining_quota(cls):
        """
        Get count of bytes we are allowed to retrieve at this time as per API rate limit.
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
        request_params = {
            'command': 'agencyList',
        }
        agencies_xml, api_call = cls.request(request_params, 'agency')
        if not agencies_xml:
            return []
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
                region = region)
            agencies.append(a)
        db.session.commit()
        return agencies

    @classmethod
    def get_routes(cls, agency, truncate=True):
        """
        Get the routes for an agency.
        There are two API commands: routeList and routeConfig.
        routeConfig is needed to get full details about a route,
        but can only show 100 routes at a time. So, use routeList
        to get a list, then batch the first 100 and piecemeal the rest.
        """
        def save_route(route_xml):
            def save_directions(route_xml, route_obj):
                directions = route_xml.findall('direction')
                for direction in directions:
                    d =  Direction.get_or_create(db.session,
                        tag = direction.get('tag'),
                        title = direction.get('title'),
                        name = direction.get('name'))
                    route_obj.directions.append(d)
            def save_stops(route_xml, route_obj):
                stops = route_xml.findall('stop')
                for stop in stops:
                    s =  Stop.get_or_create(db.session,
                        tag = stop.get('tag'),
                        title = stop.get('title'),
                        lat = stop.get('lat'),
                        lon = stop.get('lon'),
                        stop_id = stop.get('stopId'))
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
                agency_id = agency.id)
            save_directions(route_xml, r)
            save_stops(route_xml, r)
            return r

        # Get list of routes
        request_params = {
            'command': 'routeList',
            'a': agency.tag
        }
        routelist_xml, routelist_api_call = cls.request(request_params, 'route')

        if not routelist_xml:
            return []

        if truncate:
            db.session.query(Route).filter_by(agency_id=agency.id).delete()

        # Batch-import as many as Nextbus allows (100)
        request_params = {
            'command': 'routeConfig',
            'a': agency.tag,
        }
        routeconfig_xml, routeconfig_api_call = cls.request(request_params, 'route')

        routes = []
        for route in routeconfig_xml:
            r = save_route(route)
            routes.append(r)
            db.session.commit()

        # Do the rest one-by-one
        for route in routelist_xml:
            route_tag = route.get('tag')
            if route_tag not in [r.tag for r in routes]:
                request_params = {
                    'command': 'routeConfig',
                    'a': agency.tag,
                    'route': route_tag
                }
                routeconfig_xml, routeconfig_api_call = cls.request(request_params, 'route')
                r = save_route(routeconfig_xml[0])
                routes.append(r)

        db.session.commit()
        return routes

    @classmethod
    def get_predictions(cls, routes, truncate=True):
        """
        Get vehicle arrival predictions
        request parameter 'stops' is actually a list of "route|stop" pairs
        """
        all_stops = {}
        for route in routes:
            for s in route.stops:
                if route.agency.tag not in all_stops:
                    all_stops[route.agency.tag] = []
                all_stops[route.agency.tag].append("{0}|{1}".format(route.tag, s.tag))
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
                prediction_sets, api_call = cls.request(request_params, 'predictions')
                if not prediction_sets:
                    return []
                if truncate:
                    db.session.query(Prediction)\
                        .filter(
                            Prediction.route_id.in_(
                                [r.id for r in routes]
                            ))\
                        .delete(synchronize_session='fetch')
                for prediction_set in prediction_sets:
                    route_tag = prediction_set.get('routeTag')
                    route = db.session.query(Route).join(Agency)\
                        .filter(Agency.tag==agency_tag, Route.tag==route_tag).one()
                    stop_tag = prediction_set.get('stopTag')
                    stop = db.session.query(Stop)\
                        .filter_by(tag=stop_tag, route_id=route.id).one()
                    db.session.query(Stop).filter_by(route_id=route.id, tag=stop_tag)
                    for direction in prediction_set.findall('direction'):
                        xml_predictions = direction.findall('prediction')
                        for prediction in xml_predictions:
                            # lookup Direction object by tag
                            try:
                                direction = db.session.query(Direction)\
                                    .filter_by(tag=prediction.get('dirTag')).one()
                            except:
                                # This shouldn't even happen, but sometimes Nextbus puts
                                #  nonexistent direction tags here. Womp.
                                direction = None
                            # Nextbus gives epoch with milliseconds, so divide by 1k and convert.
                            predicted_seconds = int(prediction.get('epochTime'))/1000
                            predicted_time = datetime.fromtimestamp(predicted_seconds)
                            # create the prediction
                            p = Prediction.get_or_create(db.session,
                                route = route,
                                stop = stop,
                                prediction = predicted_time,
                                is_departure = prediction.get('isDeparture'),
                                has_layover = prediction.get('affectedByLayover'),
                                direction = direction,
                                vehicle = prediction.get('vehicle'),
                                block = prediction.get('block'))
                            predictions.append(p)
        db.session.commit()
        return predictions


class NextbusException(Exception):
    """ General-purpose API error """
    pass

class NextbusQuotaException(Exception):
    """ API quota exceeded. """
    pass
