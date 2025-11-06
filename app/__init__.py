import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # 1️⃣ Lees de database URL uit de omgeving
    database_url = os.getenv("DATABASE_URL")

    # 2️⃣ Fallback als er geen DATABASE_URL is ingesteld
    if not database_url:
        print("⚠️ Geen DATABASE_URL gevonden. Gebruik lokale SQLite database.")
        database_url = "sqlite:///fallback.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # 3️⃣ Test of de verbinding werkt, anders fallback naar SQLite
    try:
        with app.app_context():
            # kleine test: probeer verbinding te maken
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))

            print("✅ Verbonden met database!")
    except OperationalError as e:
        print("❌ Kan geen verbinding maken met database, gebruik SQLite in plaats.")
        print(f"Foutmelding: {e}")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fallback.db"
        db.init_app(app)

    # 4️⃣ importeer hier je blueprints, modellen, etc.
    from app import routes, models  # pas aan naar jouw structuur

    from .routes import main  # importeer de blueprint
    app.register_blueprint(main)  # registreer hem bij Flask


    return app
