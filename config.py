class Config(object):
    from datetime import timedelta
    SECRET_KEY = 'OVERRIDE THIS WITH A SECURE VALUE in instance/config.py!'
    CELERY_BROKER_URL = 'redis://'
    CELERY_RESULT_BACKEND = 'redis://'
    CELERY_ACCEPT_CONTENT = ['pickle']
    CELERYBEAT_SCHEDULE = {
        'update-agencies-every-week': {
            'task': 'celerytasks.update_agencies',
            'schedule': timedelta(days=7),
        },
        'update-routes-every-24h': {
            'task': 'celerytasks.update_routes',
            'schedule': timedelta(hours=24),
        },
        'update-predictions-every-9s': {
            'task': 'celerytasks.update_predictions',
            'schedule': timedelta(seconds=9),
        },
        'update-vehicle-locations-every-4s': {
            'task': 'celerytasks.update_vehicle_locations',
            'schedule': timedelta(seconds=4),
        },
        'delete-stale-predictions-every-5m': {
            'task': 'celerytasks.delete_stale_predictions',
            'schedule': timedelta(minutes=5),
        },
        'delete-stale-vehicle-locations-every-5m': {
            'task': 'celerytasks.delete_stale_vehicle_locations',
            'schedule': timedelta(minutes=5),
        },
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PREDICTIONS_MAX_AGE = 5 * 60;
    LOCATIONS_MAX_AGE = 5 * 60;
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
