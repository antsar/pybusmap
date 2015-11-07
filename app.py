import os
from flask import Flask
from models import db
import models

app = Flask(__name__, instance_relative_config=True)

# Load environment-specific settings from config.py
env = os.environ.get('BUSMAP_ENV', 'prod')
app.config.from_object('config.{0}Config'.format(env.capitalize()))

# Load deployment-specific settings from instance/config.cfg
app.config.from_pyfile('config.py', silent=True)

# Database init
db.init_app(app)

@app.route('/')
def just_testing():
    return str("Hello World!")

if __name__ == '__main__':
    # Run Flask
    app.run(host='0.0.0.0')

    # Run Celery
    from celery import current_app
    from celery.bin import worker
    application = current_app.get_current_object()
    worker = worker(app=application)
    options = {
        'broker': app.config['CELERY_BROKER_URL'],
        'loglevel': 'INFO',
        'traceback': True,
    }
    worker.run(**options)
