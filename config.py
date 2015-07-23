class Config(object):
    SECRET_KEY = 'CHANGE_THIS'

class ProdConfig(Config):
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_prod'

class DevConfig(Config):
    DEBUG = True
    SQLALCHEMY_URI = 'postgresql://localhost/pybusmap_dev'
