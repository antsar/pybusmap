# BusMap.py
BusMap is a real-time map of public transit vehicle locations. It's written in Python 3.4 with [Flask](http://flask.pocoo.org/).

## Setup
- Install system-wide dependencies.  
    `sudo apt-get install python python-pip python-virtualenv libxml2-dev libxsl-dev`
- Create/enter your virtualenv    
    `. venv/bin/activate`
- Install dependencies:    
    `pip install -r requirements.txt`
- Initialize database:   
    `python manage.py db upgrade`
- Run development server:    
    `python app.py`
- (Another terminal, also in virtualenv) Run celery for background task processing  
    `celery -A celerytasks.celery worker --beat`

You should now be able to access the instance on port 5000.

## Production
To run BusMap in production you need an application server. I use uWSGI in emperor mode. On Debian, this means that per-application wsgi configs belong in `/etc/uwsgi/apps-enabled/appname.ini`
Here's a sample uwsgi config for this application:

    [uwsgi]
    base = /var/www/pybusmap
    plugins = python
    home = %(base)/venv
    chdir = /var/www/pybusmap
    pythonpath = %(base)
    socket = %(base)/uwsgi.sock
    module = app
    callable = app
    uid = anton
    gid = www-data
    die-on-term = true
    vacuum = true
    smart-attach-daemon = /tmp/pybusmap-celery.pid %(home)/bin/celery -A celerytasks.celery worker --beat --pidfile=/tmp/pybusmap-celery.pid --logfile=%(base)/log/celery/%n.log

