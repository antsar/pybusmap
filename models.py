from sqlalchemy.sql.expression import ClauseElement
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class GetOrCreateModel():
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
            return instance

class Agency(db.Model, GetOrCreateModel):
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


class Region(db.Model, GetOrCreateModel):
    """
    A geographic region
    """
    __tablename__ = "region"
    id = db.Column(db.Integer, primary_key=True)

    # title - Region title
    title = db.Column(db.String, unique=True)


class Update(db.Model, GetOrCreateModel):
    """
    An event where data was updated from a source
    """
    __tablename__ = "update"
    id = db.Column(db.Integer, primary_key=True)

    # data - What was updated
    dataset = db.Column(db.Enum('agency','debug', name="dataset", native_enum=False))

    # time - When it was updated
    time = db.Column(db.DateTime, default=datetime.now)
