from flask import Flask
from flask_restful import Api

from api.events import Events
from api.health_check import HealthCheck
from api.logs import Logs
from api.runs import Runs, LastSuccessfulRun
from config import Config
from db import Session


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = Config.SQLALCHEMY_DATABASE_URI
api = Api(app)


@app.teardown_appcontext
def cleanup(_):
    Session.remove()


api.add_resource(Events, "/events")
api.add_resource(HealthCheck, "/health-check")
api.add_resource(Logs, "/logs")
api.add_resource(Runs, "/runs/<string:id>")
api.add_resource(LastSuccessfulRun, "/runs/last-success")

if __name__ == "__main__":
    app.run()
