from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import app, db

migrate = Migrate(app, db)

manager = Manager(app)
manager.add_command('db', MigrateCommand)

@manager.command
def data_init():
    from nextbus import Nextbus
    agencies = Nextbus.get_agencies(truncate=True)
    print("Got {0} agencies from Nextbus and deleted old data.".format(len(agencies)))
    for a in agencies:
        if a.tag in app.config['AGENCIES']:
            routes = Nextbus.get_routes(a, truncate=True)
            print("Got {0} routes for agency \"{1}\" from Nextbus and deleted old data.".format(len(routes), a.tag))

if __name__ == "__main__":
    manager.run()
