from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from .config import Config  # importeer je configuratiebestand

db = SQLAlchemy()  # maak database-object

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # laad de databaseconfig

    db.init_app(app)  # verbind SQLAlchemy met Flask

    from .routes import main  # importeer je routes
    app.register_blueprint(main)

    from . import models  # <--- verplaats deze regel HIER
    return app

