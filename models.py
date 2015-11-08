from sqlalchemy.sql.expression import ClauseElement
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Many-to-many mapping tables
route_stop_table = db.Table('route_stop', db.Model.metadata,
    db.Column('route_id', db.Integer, db.ForeignKey('route.id')),
    db.Column('stop_id', db.Integer, db.ForeignKey('stop.id'))
)

class BMModel():
    """
    Our own Model add-on class for adding utility functions to db.Model.
    """
    @classmethod
    def get_or_create(model, session, defaults=None, **kwargs):
        instance = session.query(model).filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
            params.update(defaults or {})
            instance = model(**params)
            session.add(instance)
            session.commit()
            return instance


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
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    agency = db.relationship("Agency")

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
    directions = db.relationship("RouteDirection", backref="route")

    # stops - Stops or stations on this route
    stops = db.relationship("Stop", secondary=route_stop_table,  backref="routes")

    # paths - Path segments which this route consists of
    # TODO: implement paths
    # Nextbus's paths are illustrative only and are said to be unreliable for
    #  .. chaining into a full route path. Leaving this out for now.


class RouteDirection(db.Model, BMModel):
    """
    A direction of a route. "Eastbound" / "Westbound", "Inbound" / "Outbound".
    """
    __tablename__ = "route_direction"
    id = db.Column(db.Integer, primary_key=True)

    # route_id - The agency which operates this route
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))

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
    """
    __tablename__ = "stop"
    id = db.Column(db.Integer, primary_key=True)

    # agency - The agency which operates this route
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    agency = db.relationship("Agency")

    # stop_id - Numeric ID
    # Not all routes/stops have this! Cannot be used as an effective index/lookup.
    stop_id = db.Column(db.Integer)

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    # This is NOT UNIQUE (even though it sounds like it should be), because
    # NextBus re-uses stop tags across routes but has DIFFERENT LAT/LON for them!
    # ...so this can't be used as an effective index/lookup for all cases.
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
    agency_id = db.Column(db.Integer, db.ForeignKey('agency.id'))
    agency = db.relationship("Agency")

    # dataset - What data was updated
    dataset = db.Column(db.Enum('agencies','routes', name="dataset", native_enum=False))

    # source - Where the data came from
    source = db.Column(db.Enum('Nextbus', name="source", native_enum=False))

    # time - When it was updated
    time = db.Column(db.DateTime, default=datetime.now)

