# PyBusMap
PyBusMap is a real-time map of public transit vehicle locations for any agency that uses
Nextbus vehicle trackers. You can see it live at [rutge.rs](http://rutge.rs).

It's written in Python 3 with [Flask](http://flask.pocoo.org/) and [SQLAlchemy](http://www.sqlalchemy.org/).
It uses [Celery](http://www.celeryproject.org/) and [requests-futures](https://github.com/ross/requests-futures)
to get real-time data from [NextBus](https://www.nextbus.com/xmlFeedDocs/NextBusXMLFeed.pdf)
at regular intervals. That is collected in a PostgreSQL database, and displayed
on a [Leaflet](http://leafletjs.com/) map.

## Status

This project is at v1. It is a feature-complete rewrite of the original
[PHP version](https://git.xhost.io/anton/bus-map). There are a few features
planned, like route planning (directions to a place) and maybe a native
mobile app (some day). **Feature [suggestions](https://ant.sr/contact) are welcome!**

## Setup for Development
- Install system-wide dependencies  
    `sudo apt-get install python python-pip python-virtualenv libxml2-dev libxsl-dev`
- Create and/or activate your virtualenv    
    Create: `virtualenv venv`
    Activate: `. venv/bin/activate`
- Install dependencies    
    `pip install -r requirements.txt`
- Initialize database   
    `python manage.py db upgrade`
- Run development server    
    `python app.py`
- (Another terminal, also in virtualenv) Run celery for background task processing  
    `celery -A celerytasks.celery worker --beat`
- Create `instance/config.py` and override the following config.py parameters:  
`    AGENCIES = ["agencytag1", "agencytag2"]
    SECRET_KEY = 'GENERATE_SOMETHING_SECURE_HERE'
    SQLALCHEMY_URI = 'postgresql://user:password@localhost/db_name'
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_URI`    
    You can generate the secret key with `apg -sm32`. Get agency tag(s) from [NextBus](http://webservices.nextbus.com/service/publicXMLFeed?command=agencyList).

You should now be able to access the instance on port 5000.

## Production
To run BusMap in production you need an application server. I use uWSGI in emperor mode. On Debian, this means that per-application uWSGI configs belong in `/etc/uwsgi/apps-enabled/appname.ini`
Here's a sample uWSGI config for this application:

    [uwsgi]
    plugins = python
    module = app
    callable = app

    # Paths
    base = /var/www/pybusmap
    home = %(base)/venv
    chdir = /var/www/pybusmap
    pythonpath = %(base)
    socket = %(base)/uwsgi.sock

    # Who the app runs as
    uid = anton
    gid = www-data

    # Worker behavior
    die-on-term = true
    vacuum = true
    smart-attach-daemon = /tmp/pybusmap-celery.pid %(home)/bin/celery -A celerytasks.celery worker --beat --pidfile=/tmp/pybusmap-celery.pid --logfile=%(base)/log/celery/%n.log

## License
PyBusMap is MIT-licensed. Please use/fork/share it. Contributions are welcome.