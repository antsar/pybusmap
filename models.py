from datetime import datetime
from flask import current_app
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, column_property
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import  NoResultFound
from sqlalchemy.schema import Table
from sqlalchemy.sql.expression import ClauseElement

db = SQLAlchemy(session_options={'autocommit': True})

route_stop = Table('route_stop', db.Model.metadata,
    db.Column('route_id', db.Integer, db.ForeignKey('route.id', ondelete="cascade")),
    db.Column('stop_id', db.Integer, db.ForeignKey('stop.id', ondelete="cascade")),
)

class BMModel():
    """ Our own Model add-on class for adding utility functions to db.Model. """
    @classmethod
    def get_one(self, session, **kwargs):
        return session.query(self).filter_by(**kwargs).first()

    @classmethod
    def get(self, session, **kwargs):
        return session.query(self).filter_by(**kwargs).all()

    @classmethod
    def get_or_create(self, session, create_method='', create_method_kwargs=None, **kwargs):
        """ Imitate Django's get_or_create() """
        try:
            return session.query(self).filter_by(**kwargs).one()
        except NoResultFound:
            kwargs.update(create_method_kwargs or {})
            new = getattr(self, create_method, self)(**kwargs)
            session.add(new)
            return new


class Agency(db.Model, BMModel):
    """ A transportation agency """
    __tablename__ = "agency"
    id = db.Column(db.Integer, primary_key=True)

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String, unique=True)

    # title - The agency's full human-readable name
    title = db.Column(db.String)

    # short_title - A shortened version of the title for compact UI's
    short_title = db.Column(db.String)

    # region - Geographic area (States, etc)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id', ondelete="cascade"))
    region = db.relationship("Region")

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="agencies")

    def serialize(self):
        return {
            'tag': self.tag,
            'title': self.title,
            'short_title': self.short_title,
        }


class ApiCall(db.Model, BMModel):
    """ A retrieval of data from a data source. """
    __tablename__ = "api_call"
    id = db.Column(db.Integer, primary_key=True)

    # Full URL of request
    url = db.Column(db.String)

    # Size of the dataset in bytes
    size = db.Column(db.Integer, default=0)

    # HTTP response code
    status = db.Column(db.Integer)

    # Any error text returned by the API
    error = db.Column(db.String)

    # Where the data came from
    source = db.Column(db.Enum('Nextbus', name="source", native_enum=False), default='Nextbus')

    # When this data was fetched
    time = db.Column(db.DateTime, default=datetime.now)

    # Parameters (request variables) of this API call
    params = db.Column(postgresql.JSON)


class Direction(db.Model, BMModel):
    """ A direction of a route. "Eastbound" / "Westbound", "Inbound" / "Outbound". """
    __tablename__ = "direction"
    __table_args__ = (
        db.UniqueConstraint('tag', 'route_id'),
    )
    id = db.Column(db.Integer, primary_key=True)

    # route_id - The agency which operates this route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String)

    # title
    title = db.Column(db.String)

    # name = A simplified/normalized name (for indexing; some routes may share this)
    name = db.Column(db.String)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="directions")

    def serialize(self):
        return {
            'tag': self.tag,
            'title': self.title,
        }


class Prediction(db.Model, BMModel):
    """ A vehicle arrival prediction """
    __tablename__ = "prediction"
    id = db.Column(db.Integer, primary_key=True)

    # route - the bus route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))
    route = db.relationship("Route")

    # prediction - the predicted time of arrival
    prediction = db.Column(db.DateTime)

    # created - when the prediction was made
    created = db.Column(db.DateTime, default=datetime.now)

    # is_departure - whether this is the time when the vehicle will depart
    is_departure = db.Column(db.Boolean)

    # has_layover - whether this is affected by a layover (prolonged stop)
    has_layover  = db.Column(db.Boolean)

    # direction - Direction for this prediction
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id', ondelete="cascade"))
    direction = db.relationship("Direction")

    # vehicle - Bus ID (not always numeric)
    vehicle = db.Column(db.String)

    # block - the vehicle's block
    block = db.Column(db.String)

    # stop - where the bus is predicted to arrive
    stop_id = db.Column(db.Integer, db.ForeignKey('stop.id'))
    stop = db.relationship("Stop", backref="predictions")

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="predictions")

    def serialize(self):
        return {
            'route': self.route.tag,
            'prediction': self.prediction,
            'created': self.created,
            'is_departure': self.is_departure,
            'has_layover': self.has_layover,
            'direction': self.direction.tag if self.direction else None,
            'vehicle': self.vehicle,
        }


class Region(db.Model, BMModel):
    """ A geographic region """
    __tablename__ = "region"
    id = db.Column(db.Integer, primary_key=True)

    # title - Region title
    title = db.Column(db.String, unique=True)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="regions")


class Route(db.Model, BMModel):
    """ A transit line: bus route, train line, etc. """
    __tablename__ = "route"
    __table_args__ = (
        db.UniqueConstraint('tag', 'agency_id'),
    )
    id = db.Column(db.Integer, primary_key=True)

    # agency - The agency which operates this route
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id', ondelete="cascade"))
    agency = db.relationship("Agency", backref="routes")

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String)

    # title
    title = db.Column(db.String)

    # short_title
    short_title = db.Column(db.String)

    # color - hex color of this route
    color = db.Column(db.String)

    # opposite_color - hex color that contrasts with the route
    opposite_color = db.Column(db.String)

    # lat_min - route extent south
    lat_min = db.Column(db.Float)

    # lat_max - route extent north
    lat_max = db.Column(db.Float)

    # lon_min - route extent west
    lon_min = db.Column(db.Float)

    # lon_max - route extent east
    lon_max = db.Column(db.Float)

    # directions - "Eastbound" / "Westbound", "Inbound" / "Outbound".
    directions = db.relationship("Direction", backref="route", lazy="joined")

    # stops - Stops or stations on this route
    stops = db.relationship("Stop", secondary=route_stop, back_populates="routes", lazy="joined", collection_class=attribute_mapped_collection("tag"), cascade="all", passive_deletes=True)

    # vehicleLocations - Locations of vehicles on this route.
    vehicle_locations = db.relationship("VehicleLocation", backref="route")

    # paths - Path segments which this route consists of
    # TODO: implement paths
    # Nextbus's paths are illustrative only and are said to be unreliable for
    #  .. chaining into a full route path. Leaving this out for now.

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="routes")

    def serialize(self):
        return {
            'agency': self.agency.serialize(),
            'tag': self.tag,
            'title': self.title,
            'short_title': self.short_title,
            'color': self.color,
            'opposite_color': self.opposite_color,
            'bounds': {
                'lat_min': self.lat_min,
                'lat_max': self.lat_max,
                'lon_min': self.lon_min,
                'lon_max': self.lon_max,
            },
            'directions': {d.tag: d.serialize() for d in self.directions},
            'stops': {s.tag: s.serialize() for s_tag, s in self.stops.items()},
        }


class Stop(db.Model, BMModel):
    """ A stop or station. Vehicles stop here and pick up or drop off passengers.
    Sometimes the driver gets out to poop.
    Stops are uniquely uniquely identifiable by (lat,lon) """
    __tablename__ = "stop"
    __table_args__ = (
        db.UniqueConstraint('tag', 'lat', 'lon'),
    )
    id = db.Column(db.Integer, primary_key=True)

    # routes - Routes which serve this stop.
    routes = db.relationship("Route", secondary=route_stop, back_populates="stops", collection_class=attribute_mapped_collection("tag"), cascade="all", passive_deletes=True)

    # stop_id - Numeric ID
    # Not all routes/stops have this! Cannot be used as an index/lookup.
    stop_id = db.Column(db.Integer)

    # Alphanumeric name (unique with route_id)
    tag = db.Column(db.String)

    # Human-readable title
    title = db.Column(db.String)

    # Latitude of this bus stop
    lat = db.Column(db.Float)

    # Longitude of this bus stop
    lon = db.Column(db.Float)

    # Count of averaged lat/lon pairs represented by lat,lon.
    lat_lon_count = db.Column(db.Integer, default=0)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="stops")

    @classmethod
    def get_or_create(self, session, create_method='', create_method_kwargs=None, **kwargs):
        """ Special logic for storing Stop objects.
            Nextbus gives the same stop tag for all routes which serve that stop, but
            the stop's provided GPS coords vary. I am assuming this to be an error, as
            buses usually stop at a shared bus shelter (at the same coords) regardless
            of what route they serve. I want to only store one instance of the stop,
            at the mean lat/lon of all provided locations. We will calculate this as a
            streaming mean, to avoid storing all lat/lon pairs. """

        # Determine if this is the same stop as another one already stored.
        existing = session.query(self).filter(
            db.and_(
                self.tag == kwargs['tag'],
                self.lat >= float(kwargs.get('lat')) - current_app.config.get('SAME_STOP_LAT', 0),
                self.lat <= float(kwargs.get('lat')) + current_app.config.get('SAME_STOP_LAT', 0),
                self.lon >= float(kwargs.get('lon')) - current_app.config.get('SAME_STOP_LON', 0),
                self.lon <= float(kwargs.get('lon')) + current_app.config.get('SAME_STOP_LON', 0),
            )).all()

        if len(existing) > 0:
            if len(existing) > 1:
                # Multiple possible matches! Find closest one. (This is an insane edge case)
                min_diff = None
                best_match = None
                for stop in existing:
                    diff = abs(stop.lat - kwargs.get('lat')) + abs(stop.lon - kwargs.get('lon'))
                    if not min_diff or diff < min_diff:
                        min_diff = diff
                        best_match = stop
                existing = best_match
            else:
                existing = existing.pop()

            # Update mean lat/lon in "stream average" fashion
            count_averaged = existing.lat_lon_count
            existing.lat = ((existing.lat * count_averaged) + kwargs.get('lat')) / (count_averaged + 1)
            existing.lon = ((existing.lon * count_averaged) + kwargs.get('lon')) / (count_averaged + 1)
            existing.lat_lon_count = count_averaged + 1
            if 'routes' in kwargs:
                for (k,v) in kwargs.get('routes').items():
                    existing.routes.set(v)
            return existing

        else:
            try:
                if 'routes' in kwargs:
                    routes = kwargs.pop('routes')
                r = session.query(self).filter_by(**kwargs).one()
                return r
            except NoResultFound:
                kwargs.update(create_method_kwargs or {})
                new = getattr(self, create_method, self)(**kwargs)
                new.routes = routes
                session.add(new)
                return new

    def serialize(self):
        return {
            'tag': self.tag,
            'title': self.title,
            'lat': self.lat,
            'lon': self.lon,
        }


class VehicleLocation(db.Model, BMModel):
    """ A vehicle geolocation for a specific time. """
    __tablename__ = "vehicle_location"
    id = db.Column(db.Integer, primary_key=True)

    # vehicle - Bus ID (not always numeric)
    vehicle = db.Column(db.String)

    # The route which this vehicle is serving
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))

    # direction - Direction for this prediction
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id', ondelete="cascade"))
    direction = db.relationship("Direction")

    # Latitude of this vehicle
    lat = db.Column(db.Float)

    # Longitude of this vehicle
    lon = db.Column(db.Float)

    # When this location was recorded
    time = db.Column(db.DateTime, default=datetime.now)

    # Whether this vehicle is currently "predictable"
    predictable = db.Column(db.Boolean)

    # Vehicle heading in degrees (0-360).
    heading = db.Column(db.Integer)

    # speed in Kilometers per hour
    speed = db.Column(db.Float)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="vehicle_locations")

    def serialize(self):
        return {
            'vehicle': self.vehicle,
            'route': self.route.tag,
            'direction': self.direction.tag if self.direction else None,
            'lat': self.lat,
            'lon': self.lon,
            'time': self.time,
            'speed': self.speed,
        }


# Hybrid properties (can't be defined until relevant classes are defined)
# Agency boundaries (derived from Route boundaries)
Agency.lat_min = column_property(db.select([db.func.min(Route.lat_min)])\
                                   .where(Route.agency_id==Agency.id))
Agency.lat_max = column_property(db.select([db.func.max(Route.lat_max)])\
                                   .where(Route.agency_id==Agency.id))
Agency.lon_min = column_property(db.select([db.func.min(Route.lon_min)])\
                                   .where(Route.agency_id==Agency.id))
Agency.lon_max = column_property(db.select([db.func.max(Route.lon_max)])\
                                   .where(Route.agency_id==Agency.id))
