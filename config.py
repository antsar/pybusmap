class Config(object):
    from datetime import timedelta
    SECRET_KEY = 'OVERRIDE THIS WITH A SECURE VALUE in instance/config.py!'
    CELERY_BROKER_URL = 'redis://'
    CELERY_RESULT_BACKEND = 'redis://'
    CELERYBEAT_SCHEDULE = {
        'get-routes-every-3s': {
            'task': 'celerytasks.get_routes',
            'schedule': timedelta(seconds=3),
            'args': ("potato",)
        },
        'test-task': {
            'task': 'celerytasks.test_task',
            'schedule': timedelta(seconds=5),
        }
    }

class ProdConfig(Config):
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_prod'
    CELERY_BROKER_URL = 'redis://localhost/0'
    CELERY_RESULT_BACKEND = 'redis://localhost/0'

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_dev'
    CELERY_BROKER_URL = 'redis://localhost/1'
    CELERY_RESULT_BACKEND = 'redis://localhost/1'
