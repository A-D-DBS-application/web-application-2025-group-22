from flask import Blueprint, render_template, request
from .models import WEBUSER
from . import db

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('login.html')

@main.route('/login', methods=['POST'])
def login():
    name = request.form.get('name')

    if not name:
        return render_template('login.html', error="Vul een naam in.")

    user = WEBUSER.query.filter_by(Name=name).first()

    if user:
        return render_template('login.html', message=f"Welkom {name}, je bent ingelogd!")
    else:
        # Optie 1: nieuwe gebruiker aanmaken als die niet bestaat
        new_user = WEBUSER(Name=name)
        db.session.add(new_user)
        db.session.commit()
        return render_template('login.html', message=f"Nieuw account aangemaakt. Welkom {name}!")
