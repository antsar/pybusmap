from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Agency(db.Model):
    """
    A transportation agency.
    """
    __tablename__ = "agency"
    id = db.Column(db.Integer, primary_key=True)

    # tag - Unique alphanumeric identifier (a.k.a. "machine name")
    tag = db.Column(db.String)

    # title - The agency's full human-readable name
    title = db.Column(db.String)

    # short_title - A shortened version of the title for compact UI's
    short_title = db.Column(db.String)

class Update(db.Model):
    """
    An event where data was updated from a source.
    """
    __tablename__ = "update"
    id = db.Column(db.Integer, primary_key=True)

    # data - What was updated
    dataset = db.Column(db.Enum('agency','debug', name="dataset", native_enum=False))

    # time - When it was updated
    time = db.Column(db.DateTime, default=datetime.now)
