import os
from flask import Flask, jsonify, render_template, request
from flask.ext.bower import Bower
from sqlalchemy.orm import joinedload
from models import db
from datetime import datetime

app = Flask(__name__, instance_relative_config=True)

# Load environment-specific settings from config.py
env = os.environ.get('BUSMAP_ENV', 'prod')
app.config.from_object('config.{0}Config'.format(env.capitalize()))

# Load deployment-specific settings from instance/config.cfg
app.config.from_pyfile('config.py', silent=True)

# Database init
db.init_app(app)

Bower(app)

# Flask Web Routes
@app.route('/')
def map():
    from models import Agency
    # TODO: serve different agency depending on cookie (or special domain)
    agency_tag = app.config['AGENCIES'][0]
    agency = db.session.query(Agency).filter(Agency.tag==agency_tag).one()
    return render_template('map.html', agency=agency, config=app.config)

@app.route('/ajax')
def ajax():
    # TODO: OPTIMIZE THIS SHIT.
    # Over 1sec/request just to get predictions? Fuck that noise.
    dataset = request.args.get('dataset')
    agency = request.args.get('agency')
    def routes():
        from models import Agency, Route, RouteStop, Stop
        routes = db.session.query(Route).join(Agency)\
            .filter(Agency.tag==agency).all()
        stops = db.session.query(Stop).options(joinedload(Stop.routes))\
            .filter(Stop.routes.any(Route.id.in_([r.id for r in routes]))).all()
        return {
            "routes": {r.tag: r.serialize() for r in routes},
            "stops": {s.id: s.serialize() for s in stops}
        }

    def vehicles():
        from models import Agency, Route, VehicleLocation, Prediction
        vehicle_locations = db.session.query(VehicleLocation)\
            .join(VehicleLocation.route).join(Route.agency)\
            .filter(Agency.tag==agency).all()
        now = datetime.now()

        p_inner = db.session.query(Prediction.vehicle, Prediction.stop_id,
                                   db.func.max(Prediction.api_call_id).label("api_call_id"))\
                            .group_by(Prediction.vehicle, Prediction.stop_id)\
                            .subquery()
        predictions = db.session.query(Prediction).join(p_inner, db.and_(
                p_inner.c.api_call_id == Prediction.api_call_id,
                p_inner.c.vehicle == Prediction.vehicle,
                p_inner.c.stop_id == Prediction.stop_id
            )).filter(
                Agency.tag==agency,
                Prediction.prediction >= now)\
            .group_by(Prediction.id, Prediction.vehicle, Prediction.stop_id)\
            .all()

        z = {
                "locations": {v.vehicle: v.serialize() for v in vehicle_locations},
                "predictions": {p.id: p.serialize() for p in predictions}
        }
        return z

    if dataset == "routes":
        r = jsonify(routes())
    elif dataset == "vehicles":
        r = jsonify(vehicles())
    return r

if __name__ == '__main__':
    # Run Flask
    app.run(host='0.0.0.0')
