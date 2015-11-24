import time
import sys
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import app, db
from celerytasks import update_agencies, update_routes

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def data_init(agencies_only=False):
    from nextbus import Nextbus
    start = time.time()
    agencies = Nextbus.get_agencies()
    print("Got {0} agencies from Nextbus in {1:.2f} seconds.".format(len(agencies), time.time() - start))
    if not agencies_only:
        for a in agencies:
            a_start = time.time()
            if a.tag in app.config['AGENCIES']:
                routes = Nextbus.get_routes(a.tag)
                print("Got {0} routes for agency \"{1}\" in {2:.2f} seconds.".format(len(routes), a.tag, time.time() - a_start))
    print("Total time: {0:.2f} seconds".format(time.time() - start))

@manager.command
def update_predictions(loop=False,agencies=None):
    def do_it(agencies):
        from nextbus import Nextbus
        from models import Agency
        start = time.time()
        if agencies:
            agencies = agencies.split(",")
        if not agencies:
            agencies = app.config['AGENCIES']
        agencies = db.session.query(Agency).filter(Agency.tag.in_(agencies)).all()
        prediction_count = 0
        route_count = 0
        for agency in agencies:
            prediction_count += len(Nextbus.get_predictions(agency.routes, truncate=False))
            route_count += len(agency.routes)
        elapsed = time.time() - start
        print("Got {0} predictions for {1} agencies ({2} routes) in {3:0.2f} seconds."\
              .format(prediction_count, len(agencies), route_count, elapsed))
    if loop:
        while True:
            do_it(agencies)
    else:
        do_it(agencies)

@manager.command
def api_quota(tail=False):
    """
    Check the API quota balance.
    Use --tail for updates every 0.25 seconds.
    """
    from nextbus import Nextbus
    if tail:
        try:
            while True:
                remaining_mb = Nextbus.remaining_quota() / 1024**2
                sys.stdout.write("\rNextbus Quota: {0:.3f} MB remaining.".format(remaining_mb))
                sys.stdout.flush()
                time.sleep(0.25)
        except KeyboardInterrupt:
            print("")
            sys,exit()
    else:
        remaining_mb = Nextbus.remaining_quota() / 1024**2
        print("Nextbus Quota: {0:.3f} MB remaining.".format(remaining_mb))

if __name__ == "__main__":
    manager.run()
