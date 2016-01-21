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
    AGENCIES = ['rutgers']

    # Distance within stops with the same tag will be averaged to one lat/lon point.
    # Guide: http://gis.stackexchange.com/a/8674
    # 0.001 = 110 Meters (football field)
    SAME_STOP_LAT = 0.005
    SAME_STOP_LON = 0.005

    # Map display parameters
    MAP_CUSTOM_ATTRIBUTION = '<a href="https://ant.sr/">ant.sr</a>'
    MAP_DATA_ATTRIBUTION = '<a href="http://cartodb.com/attributions#basemaps">CartoDB</a>'
    MAP_ERROR_TILE_URL = 'http://tiles.antsar-static.com/generic/tile-blank-black.png'
    MAP_TILE_URL = 'http://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
    MAP_TILE_SUBDOMAINS = ['a', 'b', 'c']
    MAP_TILESET = 'rutgers-black'
    MAP_LAT_PADDING = 0.01
    MAP_LON_PADDING = 0.01

class ProdConfig(Config):
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_prod'
    CELERY_BROKER_URL = 'redis://localhost/0'
    CELERY_RESULT_BACKEND = 'redis://localhost/0'

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_dev'
    CELERY_BROKER_URL = 'redis://localhost/1'
    CELERY_RESULT_BACKEND = 'redis://localhost/1'
