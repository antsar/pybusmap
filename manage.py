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
def data_init():
    from nextbus import Nextbus
    agencies = Nextbus.get_agencies()
    print("Got {0} agencies from Nextbus.".format(len(agencies)))
    for a in agencies:
        if a.tag in app.config['AGENCIES']:
            routes = Nextbus.get_routes(a)
            print("Got {0} routes for agency \"{1}\" from Nextbus.".format(len(routes), a.tag))

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
