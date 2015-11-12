from celery import Celery
from celery.utils.log import get_task_logger
from datetime import timedelta
from app import app, db
from nextbus import Nextbus

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

logger = get_task_logger(__name__)

# Task definitions:
@celery.task()
def update_agencies():
    Nextbus.get_agencies()

@celery.task()
def update_routes(agencies=None):
    from models import Agency
    if not agencies:
        agencies = app.config['AGENCIES']
    route_count = 0
    for agency in db.session.query(Agency).all():
        if agency.tag in agencies:
            route_count += len(Nextbus.get_routes(agency))
    print("update_routes: Got {0} routes for {1} agencies".format(prediction_count, len(agencies)))

@celery.task()
def update_predictions(agencies=None):
    from models import Agency
    if not agencies:
        agencies = app.config['AGENCIES']
    prediction_count = 0
    for agency_tag in agencies:
        agency = db.session.query(Agency).filter_by(tag=agency_tag).one()
        prediction_count += len(Nextbus.get_predictions(agency.routes))
    print("update_predictions: Got {0} predictions {1} agencies".format(prediction_count, len(agencies)))
