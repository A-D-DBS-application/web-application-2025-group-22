from app import create_app, db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # maakt tabellen aan in Supabase als ze nog niet bestaan
    app.run(debug=True)
