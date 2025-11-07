from app import create_app, db

app = create_app()

with app.app_context():
    db.create_all()  # maakt tabellen aan in Supabase als ze nog niet bestaan

if __name__ == '__main__':
    app.run(debug=True)

# gagaga