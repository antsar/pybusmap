import os
from flask import Flask

app = Flask(__name__, instance_relative_config=True)

# Load environment-specific settings from config.py
env = os.environ.get('BUSMAP_ENV', 'prod')
app.config.from_object('config.{0}Config'.format(env.capitalize()))

# Load deployment-specific settings from instance/config.cfg
app.config.from_pyfile('config.py', silent=True)

@app.route('/')
def just_testing():
    return str(app.config['SQLALCHEMY_URI'])
    return "Brotato!"

if __name__ == '__main__':
    app.run(host='0.0.0.0')
