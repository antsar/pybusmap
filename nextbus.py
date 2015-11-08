from requests import get
from lxml import etree
import json
from models import Agency, Region, Route, RouteDirection, Stop, Update
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
        if one:
            return tree.findall(tagName)[0]
        else:
            return tree.findall(tagName)


    @classmethod
    def get_agencies(cls):
        """
        Get a list of agencies
        """
        agencies = []
        request = {
            'command': 'agencyList',
        }
        for agency in cls.request(request, 'agency'):
            region = Region.get_or_create(db.session, title=agency.get('regionTitle'))
            a = Agency.get_or_create(db.session,
                tag = agency.get('tag'),
                title = agency.get('title'),
                short_title = agency.get('shortTitle'),
                region = region)
            agencies.append(a)
        db.session.add(Update(dataset="agency"))
        db.session.commit()
        return agencies

    @classmethod
    def get_routes(cls, agency):
        """
        Get the routes for an agency.
        There are two API commands: routeList and routeConfig.
        routeConfig is needed to get full details about a route,
        but can only show 100 routes at a time. So, use routeList
        to get a list, then batch the first 100 and piecemeal the rest.
        """
        routes = []
        def save_route(route_xml):
            def save_directions(route_xml, route_obj):
                directions = route_xml.findall('direction')
                for direction in directions:
                    d =  RouteDirection.get_or_create(db.session,
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
                        stop_id = stop.get('stopId'),
                        agency_id = agency.id)
                    route_obj.stops.append(s)
            r = Route.get_or_create(db.session,
                tag = route_xml.get('tag'),
                title = route_xml.get('title'),
                color = route_xml.get('color'),
                opposite_color = route_xml.get('oppositeColor'),
                lat_min = route_xml.get('latMin'),
                lat_max = route_xml.get('latMax'),
                lon_min = route_xml.get('lonMin'),
                lon_max = route_xml.get('lonMax'))
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

        db.session.commit()
        return routes
