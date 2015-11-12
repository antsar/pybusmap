from requests import get
from lxml import etree
import json
from datetime import datetime
from models import Agency, Region, Route, Direction, Stop, Update, Prediction
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

    @classmethod
    def request(cls, params, tagName, one=False):
        """
        Perform an API request specified by params
        and return all elements called tagName
        """
        response = get(cls.api_url, params)
        xmlroot = etree.fromstring(response.content)
        tree = etree.ElementTree(xmlroot)
        if len(tree.findall('Error')) > 0:
            error_xml_string  = etree.tostring(xmlroot)
            raise(Exception(str(params) + error_xml_string))
        if one:
            return tree.findall(tagName)[0]
        else:
            return tree.findall(tagName)


    @classmethod
    def get_agencies(cls, truncate=True):
        """
        Get a list of agencies
        """
        agencies = []
        request = {
            'command': 'agencyList',
        }
        if truncate:
            db.session.query(Agency).delete()
        for agency in cls.request(request, 'agency'):
            region = Region.get_or_create(db.session,
                title=agency.get('regionTitle'))
            a = Agency.get_or_create(db.session,
                tag = agency.get('tag'),
                title = agency.get('title'),
                short_title = agency.get('shortTitle'),
                region = region)
            agencies.append(a)
        db.session.add(Update(dataset="agencies"))
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
        routes = []
        if truncate:
            db.session.query(Route).delete()
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
        request = {
            'command': 'routeList',
            'a': agency.tag
        }
        route_list = cls.request(request, 'route')


        # Batch-import as many as we can (allegedly 100)
        request = {
            'command': 'routeConfig',
            'a': agency.tag,
        }
        route_config = cls.request(request, 'route')
        done_tags = []
        for route in route_config:
            r = save_route(route)
            done_tags.append(r.tag)
            routes.append(r)
            db.session.commit()

        # Do the rest one-by-one
        for route in route_list:
            route_tag = route.get('tag')
            if route_tag not in done_tags:
                request = {
                    'command': 'routeConfig',
                    'a': agency.tag,
                    'route': route_tag
                }
                xml_route = cls.request(request, 'route', one=True)
                r = save_route(xml_route)
                routes.append(r)

        db.session.add(Update(dataset="routes", agency=agency))
        db.session.commit()
        return routes

    @classmethod
    def get_predictions(cls, routes, truncate=True):
        """
        Get vehicle arrival predictions
        request parameter 'stops' is actually a list of "route|stop" pairs
        """
        if truncate:
            db.session.query(Prediction)\
                .filter(
                    Prediction.route_id.in_(
                        [r.id for r in routes]
                    ))\
                .delete(synchronize_session='fetch')
        stops = []
        for route in routes:
            for s in route.stops:
               stops.append("{0}|{1}".format(route.tag, s.tag))
        # Batch into groups of 150 route|stop pairs, as per API limits
        api_limit = 150
        batches = [stops[x:x+api_limit] for x in range(0, len(stops), api_limit)]
        predictions = []
        for stops in batches:
            request = {
                'command': 'predictionsForMultiStops',
                'a': route.agency.tag,
                'stops': stops
            }
            prediction_sets = cls.request(request, 'predictions')
            for prediction_set in prediction_sets:
                for direction in prediction_set.findall('direction'):
                    xml_predictions = direction.findall('prediction')
                    for prediction in xml_predictions:
                        # lookup Direction object by tag
                        direction = db.session.query(Direction)\
                            .filter_by(tag=prediction.get('dirTag')).one()
                        # Nextbus gives epoch with milliseconds, so divide by 1k and convert.
                        predicted_seconds = int(prediction.get('epochTime'))/1000
                        predicted_time = datetime.fromtimestamp(predicted_seconds)
                        # create the prediction
                        p = Prediction.get_or_create(db.session,
                            route = route,
                            prediction = predicted_time,
                            is_departure = prediction.get('isDeparture'),
                            has_layover = prediction.get('affectedByLayover'),
                            direction = direction,
                            vehicle = prediction.get('vehicle'),
                            block = prediction.get('block'))
                        predictions.append(p)
        db.session.add(Update(dataset="predictions", route=route))
        db.session.commit()
        return predictions


