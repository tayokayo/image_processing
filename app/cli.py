from flask.cli import FlaskGroup
from . import create_app

def create_cli_app():
    return create_app()

cli = FlaskGroup(create_app=create_cli_app)