from celery import Celery
from datetime import timedelta
from app import app, db
from nextbus import NextBus

"""
Celery is a task queue for background task processin. It is used in BusMap
for scheduled tasks, which are configured in this file.

The task execution schedule can be found in config.py.
"""


# Create new Celery object with configured broker; get other cfg params
celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# This wraps task execution in an app context (for db session, etc)
TaskBase = celery.Task
class ContextTask(TaskBase):
    abstract = True
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return TaskBase.__call__(self, *args, **kwargs)
celery.Task = ContextTask

# Task definitions:
@celery.task()
def update_agencies():
    NextBus.get_agencies()

@celery.task()
def update_routes(agencies):
    from models import Agency
    for agency in db.session.query(Agency).all():
        if agency.tag in agencies:
            NextBus.get_routes(agency)
