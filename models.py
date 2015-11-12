from sqlalchemy.sql.expression import ClauseElement
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import  NoResultFound
from datetime import datetime

db = SQLAlchemy()

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
            session.flush()
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
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    region = db.relationship("Region")


class Prediction(db.Model, BMModel):
    """
    A vehicle arrival prediction
    """
    __tablename__ = "prediction"
    id = db.Column(db.Integer, primary_key=True)

    # route - the bus route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
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
    direction_id = db.Column(db.Integer, db.ForeignKey('direction.id'))
    direction = db.relationship("Direction")

    # vehicle - Bus ID (not always numeric)
    vehicle = db.Column(db.String)

    # block - the vehicle's block
    block = db.Column(db.String)


class Region(db.Model, BMModel):
    """
    A geographic region
    """
    __tablename__ = "region"
    id = db.Column(db.Integer, primary_key=True)

    # title - Region title
    title = db.Column(db.String, unique=True)


class Route(db.Model, BMModel):
    """
    A bus route, train line, etc.
    """
    __tablename__ = "route"
    id = db.Column(db.Integer, primary_key=True)

    # agency - The agency which operates this route
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id', ondelete="cascade"))
    agency = db.relationship("Agency", backref="routes")

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String, unique=True)

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

    # paths - Path segments which this route consists of
    # TODO: implement paths
    # Nextbus's paths are illustrative only and are said to be unreliable for
    #  .. chaining into a full route path. Leaving this out for now.


class Direction(db.Model, BMModel):
    """
    A direction of a route. "Eastbound" / "Westbound", "Inbound" / "Outbound".
    """
    __tablename__ = "direction"
    id = db.Column(db.Integer, primary_key=True)

    # route_id - The agency which operates this route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String, unique=True)

    # title
    title = db.Column(db.String)

    # name = A simplified/normalized name (for indexing; some routes may share this)
    name= db.Column(db.String)


class Stop(db.Model, BMModel):
    """
    A stop or station. Vehicles stop here and pick up or drop off passengers.
    Sometimes the driver gets out to poop.
    Stops are uniquely uniquely identifiable by route:stop_tag
    """
    __tablename__ = "stop"
    id = db.Column(db.Integer, primary_key=True)

    # route_id - The agency which operates this route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))

    # stop_id - Numeric ID
    # Not all routes/stops have this! Cannot be used as an effective index/lookup.
    stop_id = db.Column(db.Integer)

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String)

    # title - Human-readable name for stop
    title = db.Column(db.String)

    # lat
    lat = db.Column(db.Float)

    # lon
    lon = db.Column(db.Float)


class Update(db.Model, BMModel):
    """
    An event when data was updated from a source
    """
    __tablename__ = "update"
    id = db.Column(db.Integer, primary_key=True)

    # agency - Which agency this data is for
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id', ondelete="cascade"))
    agency = db.relationship("Agency")

    # route - Which agency this data is for
    route_Id = db.Column(db.Integer, db.ForeignKey('route.id', ondelete="cascade"))
    route = db.relationship("Route")

    # dataset - What data was updated
    dataset = db.Column(db.Enum(
        'agencies','routes', 'predictions',
        name="dataset", native_enum=False))

    # source - Where the data came from
    source = db.Column(db.Enum('Nextbus', name="source", native_enum=False))

    # time - When it was updated
    time = db.Column(db.DateTime, default=datetime.now)

