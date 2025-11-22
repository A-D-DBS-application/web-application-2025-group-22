from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from sqlalchemy import func

from .models import WEBUSER, CLIENT, SUPPLIER, PRODUCT, ORDER, COST
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
        # Redirect naar registratiepagina
        return jsonify({"status": "redirect", "url": "/register"})

    elif action == "login":
        if not user:
            return jsonify({"status": "error", "message": "Account niet gevonden. Gelieve eerst aan te melden."})
        return jsonify({"status": "success", "message": f"Ingelogd als {name}"})

    return jsonify({"status": "error", "message": "Ongeldige actie."})

# 📝 Registratiepagina
@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        supplier_id = request.form.get('supplier_id')

        if not username or not email or not supplier_id:
            return render_template('register.html', message="Vul alle velden in.")

        existing_user = WEBUSER.query.filter_by(Name=username).first()
        if existing_user:
            return render_template('register.html', message="Gebruiker bestaat al. Log in.")

        new_user = WEBUSER(Name=username, Email=email, SUPPLIER_ID=int(supplier_id))
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('main.home'))

    # GET
    suppliers = SUPPLIER.query.all()
    return render_template('register.html', suppliers=suppliers)

# 🏡 Homepagina
@main.route('/home')
def home_page():
    return render_template('home.html')


# 👥 Client-overzichtspagina
@main.route('/clients')
def clients():
    clients = CLIENT.query.all()
    
    client_totals = {
        client.CLIENT_ID: {
            "total_revenue": 0,
            "total_production_cost": 0,
            "total_transport_cost": 0,
            "total_storage_cost": 0,
        }
        for client in clients
    }

    aggregate_rows = (
        db.session.query(
            CLIENT.CLIENT_ID,
            func.coalesce(func.sum(ORDER.total_sell_price), 0).label("total_revenue"),
            func.coalesce(func.sum(ORDER.quantity * PRODUCT.Unit_cost), 0).label("total_production_cost"),
            func.coalesce(func.sum(COST.Total_transport_cost), 0).label("total_transport_cost"),
            func.coalesce(func.sum(COST.Total_stockage_cost), 0).label("total_storage_cost"),
        )
        .outerjoin(ORDER, CLIENT.CLIENT_ID == ORDER.CLIENT_ID)
        .outerjoin(PRODUCT, ORDER.PRODUCT_NR == PRODUCT.PRODUCT_NR)
        .outerjoin(COST, ORDER.FACTUUR_NR == COST.FACTUUR_NR)
        .group_by(CLIENT.CLIENT_ID)
        .all()
    )

    for row in aggregate_rows:
        client_totals[row.CLIENT_ID] = {
            "total_revenue": row.total_revenue,
            "total_production_cost": row.total_production_cost,
            "total_transport_cost": row.total_transport_cost,
            "total_storage_cost": row.total_storage_cost,
        }

    countries = sorted({client.Country for client in clients if client.Country})

    return render_template(
        'clients.html',
        clients=clients,
        client_totals=client_totals,
        countries=countries,
    )

# 👥 Webusers-overzichtspagina
@main.route('/webusers')
def webusers():
    webusers_list = WEBUSER.query.all()
    return render_template('webusers.html', webusers=webusers_list)


# 👥 Suppliers-overzichtspagina
@main.route('/suppliers')
def suppliers():
    suppliers = SUPPLIER.query.all()
    return render_template('suppliers.html', suppliers=suppliers)

# 📦 Products-overzichtspagina
@main.route('/products')
def products():
    products = PRODUCT.query.all()
    return render_template('products.html', products=products)

# 🛒 Orders-overzichtspagina
@main.route('/orders')
def orders():
    orders = ORDER.query.all()
    return render_template('orders.html', orders=orders)

# 💰 Costs-overzichtspagina
@main.route('/costs')
def costs():
    costs = COST.query.all()
    return render_template('costs.html', costs=costs)
