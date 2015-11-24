from celery.utils.log import get_task_logger
from flask.ext.celery import Celery
from datetime import datetime, timedelta
from app import app, db
from models import Prediction
from nextbus import Nextbus

"""
Celery is a task queue for background task processing. We're using it
for scheduled tasks, which are configured in this file.

The task execution schedule can be found/tweaked in config.py.
"""


# Create new Celery object with configured broker; get other cfg params
celery = Celery(app)
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
    """
    Refresh our list of Agencies from NextBus
    """
    Nextbus.get_agencies(truncate=True)

@celery.task()
def update_routes(agencies=None):
    """
    Refresh our list of Routes, Stops, and Directions from Nextbus
    """
    from models import Agency
    if not agencies:
        agencies = app.config['AGENCIES']
    route_count = 0
    for agency_tag in agencies:
        route_count += len(Nextbus.get_routes(agency_tag, truncate=True))
    print("update_routes: Got {0} routes for {1} agencies"\
          .format(route_count, len(agencies)))

@celery.task()
def update_predictions(agencies=None):
    """
    Get the latest vehicle arrival predictions from Nextbus
    """
    from models import Agency
    import time
    start = time.time()
    if not agencies:
        agencies = app.config['AGENCIES']
    prediction_count = 0
    route_count = 0
    for agency_tag in agencies:
        agency = db.session.query(Agency).filter_by(tag=agency_tag).one()
        prediction_count += len(Nextbus.get_predictions(agency.routes, truncate=False))
        route_count += len(agency.routes)
    elapsed = time.time() - start
    print("update_predictions: Got {0} predictions for {1} agencies ({2} routes) in {3:0.2f} sec."\
          .format(prediction_count, len(agencies), route_count, elapsed))

@celery.task()
def update_vehicles(agencies=None):
    """
    Get the latest vehicle locations (coords/speed/heading) from NextBus
    """
    from models import Agency
    if not agencies:
        agencies = app.config['AGENCIES']
    vehicle_count = 0
    route_count = 0

@celery.task()
def delete_stale_predictions():
    """
    Delete predictions older than PREDICTIONS_MAX_AGE.
    """
    delete = Nextbus.delete_stale_predictions()
    print("{0} stale predictions deleted".format(delete))
