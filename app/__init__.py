from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
from .config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    try:
        with app.app_context():
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("✅ Verbonden met Supabase!")
    except OperationalError as e:
        print("❌ Kan geen verbinding maken met Supabase, gebruik SQLite fallback.")
        print(f"Foutmelding: {e}")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fallback.db"

    from .routes import main
    app.register_blueprint(main)

    return app