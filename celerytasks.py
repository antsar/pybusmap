from celery import Celery
from datetime import timedelta
from app import app, db
from models import Update

celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
TaskBase = celery.Task
class ContextTask(TaskBase):
    abstract = True
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return TaskBase.__call__(self, *args, **kwargs)
celery.Task = ContextTask

@celery.task()
def get_routes(word):
    # get bus routes from NextBus and store them in db
    print("get_routes {0}".format(word))
    return True;


@celery.task()
def test_task():
    # Testing database access from celery task
    test_update = Update(dataset='debug')
    db.session.add(test_update)
    db.session.commit()
    print("Added {0}".format(test_update))
