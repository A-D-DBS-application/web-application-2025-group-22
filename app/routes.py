from flask import Blueprint, render_template, request, jsonify
from .models import WEBUSER, CLIENT
from . import db

main = Blueprint('main', __name__)

# 🏠 Loginpagina
@main.route('/')
def home():
    return render_template('login.html')

# 🔑 Login / Signup functionaliteit
@main.route('/login', methods=['POST'])
def login():
    name = request.form.get('name')
    action = request.form.get('action')  # "login" of "signup"

    if not name:
        return jsonify({"status": "error", "message": "Vul een naam in."})

    user = WEBUSER.query.filter_by(Name=name).first()

    if action == "signup":
        if user:
            return jsonify({"status": "error", "message": "Account bestaat al. Log in."})
        new_user = WEBUSER(Name=name)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Aangemeld als {name}"})

    elif action == "login":
        if not user:
            return jsonify({"status": "error", "message": "Account niet gevonden. Meld je eerst aan."})
        return jsonify({"status": "success", "message": f"Ingelogd als {name}"})

    return jsonify({"status": "error", "message": "Ongeldige actie."})


# 🏡 Homepagina
@main.route('/home')
def home_page():
    return render_template('home.html')


# 👥 Client-overzichtspagina
@main.route('/clients')
def clients():
    clients = CLIENT.query.all()
    return render_template('clients.html', clients=clients)