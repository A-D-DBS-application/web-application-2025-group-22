import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from .config import Config

db = SQLAlchemy()

def create_app():
    # Bepaal de absolute pad naar de app-map (waar dit bestand staat)
    base_dir = os.path.abspath(os.path.dirname(__file__))

    # Initialiseer de Flask-app en wijs expliciet naar de juiste mappen
    app = Flask(
        __name__,
        static_folder=os.path.join(base_dir, "static"),
        template_folder=os.path.join(base_dir, "templates")
    )

    # Configuratie en database
    app.config.from_object(Config)
    db.init_app(app)

    # Test de verbinding met Supabase
    try:
        with app.app_context():
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("✅ Verbonden met Supabase!")
    except OperationalError as e:
        print("❌ Kan geen verbinding maken met Supabase, gebruik SQLite fallback.")
        print(f"Foutmelding: {e}")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fallback.db"

    # Registreer de blueprint(s)
    from .routes import main
    app.register_blueprint(main)

    return app

