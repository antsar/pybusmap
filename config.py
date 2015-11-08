class Config(object):
    from datetime import timedelta
    SECRET_KEY = 'OVERRIDE THIS WITH A SECURE VALUE in instance/config.py!'
    CELERY_BROKER_URL = 'redis://'
    CELERY_RESULT_BACKEND = 'redis://'
    CELERYBEAT_SCHEDULE = {
        'update-routes-every-24h': {
            'task': 'celerytasks.update_routes',
            'schedule': timedelta(days=1),
        },
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AGENCIES = ["SAMPLE_AGENCY"]

class ProdConfig(Config):
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_prod'
    CELERY_BROKER_URL = 'redis://localhost/0'
    CELERY_RESULT_BACKEND = 'redis://localhost/0'

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_dev'
    CELERY_BROKER_URL = 'redis://localhost/1'
    CELERY_RESULT_BACKEND = 'redis://localhost/1'
