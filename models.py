from sqlalchemy.sql.expression import ClauseElement
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import  NoResultFound
from sqlalchemy.dialects import postgresql
from datetime import datetime

db = SQLAlchemy(session_options={'autocommit': True})

class BMModel():
    """
    Our own Model add-on class for adding utility functions to db.Model.
    """
    @classmethod
    def get_one(cls, session, **kwargs):
        return session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def get(cls, session, **kwargs):
        return session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def get_or_create(cls, session, create_method='', create_method_kwargs=None, **kwargs):
        """ Imitate Django's get_or_create() """
        try:
            return session.query(cls).filter_by(**kwargs).one()
        except NoResultFound:
            kwargs.update(create_method_kwargs or {})
            new = getattr(cls, create_method, cls)(**kwargs)
            session.add(new)
            return new


class Agency(db.Model, BMModel):
    """
    A transportation agency
    """
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


class Prediction(db.Model, BMModel):
    """
    A vehicle arrival prediction
    """
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


class Region(db.Model, BMModel):
    """
    A geographic region
    """
    __tablename__ = "region"
    id = db.Column(db.Integer, primary_key=True)

    # title - Region title
    title = db.Column(db.String, unique=True)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="regions")


class Route(db.Model, BMModel):
    """
    A bus route, train line, etc.
    """
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
    directions = db.relationship("Direction", backref="route")

    # stops - Stops or stations on this route
    stops = db.relationship("Stop", backref="route")

    # vehicleLocations - Locations of vehicles on this route.
    vehicle_locations = db.relationship("VehicleLocation", backref="route")

    # paths - Path segments which this route consists of
    # TODO: implement paths
    # Nextbus's paths are illustrative only and are said to be unreliable for
    #  .. chaining into a full route path. Leaving this out for now.

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="routes")


class Direction(db.Model, BMModel):
    """
    A direction of a route. "Eastbound" / "Westbound", "Inbound" / "Outbound".
    """
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
    name= db.Column(db.String)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="directions")


class Stop(db.Model, BMModel):
    """
    A stop or station. Vehicles stop here and pick up or drop off passengers.
    Sometimes the driver gets out to poop.
    Stops are uniquely uniquely identifiable by route:tag
    """
    __tablename__ = "stop"
    __table_args__ = (
        db.UniqueConstraint('tag', 'route_id'),
    )
    id = db.Column(db.Integer, primary_key=True)

    # The route which this stop is a part of.
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))

    # stop_id - Numeric ID
    # Not all routes/stops have this! Cannot be used as an index/lookup.
    stop_id = db.Column(db.Integer)

    # Unique alphanumeric name
    tag = db.Column(db.String)

    # Human-readable title
    title = db.Column(db.String)

    # Latitude of this bus stop
    lat = db.Column(db.Float)

    # Longitude of this bus stop
    lon = db.Column(db.Float)

    # API Request which was used to retrieve this data
    api_call_id = db.Column(db.Integer, db.ForeignKey('api_call.id', ondelete="set null"))
    api_call = db.relationship("ApiCall", backref="stops")


class VehicleLocation(db.Model, BMModel):
    """
    A vehicle geolocation for a specific time.
    """
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


class ApiCall(db.Model, BMModel):
    """
    A retrieval of data from a data source.
    """
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
