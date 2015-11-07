class Config(object):
    from datetime import timedelta
    SECRET_KEY = 'CHANGE_THIS'
    CELERY_BROKER_URL = 'redis://'
    CELERY_RESULT_BACKEND = 'redis://'
    # scheduled tasks
    CELERYBEAT_SCHEDULE = {
        'get-routes-every-30s': {
            'task': 'celerytasks.get_routes',
            'schedule': timedelta(seconds=30),
            'args': ("potato",)
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
