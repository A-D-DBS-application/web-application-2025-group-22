from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import func
from . import db

from .models import (
    WEBUSER,
    CLIENT,
    SUPPLIER,
    PRODUCT,
    ORDER,
    ORDER_LINE,
    BRAND,
    PRODUCT_COST
)

main = Blueprint("main", __name__)


# -------------------------
# LOGIN + REGISTER
# -------------------------
@main.route("/")
def home():
    return render_template("login.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    name = request.form.get("name")
    action = request.form.get("action")

    if not name:
        return render_template("login.html", message="Vul een naam in.")

    user = WEBUSER.query.filter_by(Name=name).first()

    if action == "signup":
        if user:
            return render_template("login.html", message="Account bestaat al.")
        return redirect(url_for("main.register"))

    if action == "login":
        if not user:
            return render_template("login.html", message="Gebruiker niet gevonden.")
        return redirect(url_for("main.home_page"))

    return render_template("login.html", message="Ongeldige actie.")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        supplier_id = request.form.get("supplier_id")

        if not username or not email or not supplier_id:
            return render_template("register.html", message="Vul alles in.", suppliers=SUPPLIER.query.all())

        existing = WEBUSER.query.filter_by(Name=username).first()
        if existing:
            return render_template("register.html", message="Gebruiker bestaat al.", suppliers=SUPPLIER.query.all())

        new_user = WEBUSER(Name=username, Email=email, SUPPLIER_id=supplier_id)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("main.home"))

    suppliers = SUPPLIER.query.all()
    return render_template("register.html", suppliers=suppliers)


@main.route("/home")
def home_page():
    return render_template("home.html")


# -------------------------
# CLIENTS LIST
# -------------------------
@main.route("/clients")
def clients():

    clients = CLIENT.query.all()

    # basis datastructuur voor elke client
    client_totals = {
        c.CLIENT_ID: {
            "total_revenue": 0,
            "total_production_cost": 0,
            "total_transport_cost": 0,
            "total_storage_cost": 0,
        }
        for c in clients
    }

    # -------------------------
    # ✔ OMZET (Paid_price ALLEEN, geen quantity)
    # -------------------------
    revenue_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER_LINE.Paid_price).label("total_revenue")
        )
        .join(ORDER_LINE, ORDER.ORDER_NR == ORDER_LINE.ORDER_NR)
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in revenue_rows:
        client_totals[row.CLIENT_ID]["total_revenue"] = float(row.total_revenue or 0)

    # -------------------------
    # ✔ PRODUCTION COST
    # = Quantity × Production_cost per product
    # -------------------------
    production_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER_LINE.Quantity * PRODUCT_COST.Production_cost).label("total_production_cost"),
        )
        .join(ORDER_LINE, ORDER.ORDER_NR == ORDER_LINE.ORDER_NR)
        .join(PRODUCT, PRODUCT.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .join(PRODUCT_COST, PRODUCT_COST.PRODUCT_ID == PRODUCT.PRODUCT_ID)
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in production_rows:
        client_totals[row.CLIENT_ID]["total_production_cost"] = float(row.total_production_cost or 0)

    # LANDEN DYNAMISCH LADEN
    countries = sorted({c.Country for c in clients if c.Country})

    return render_template(
        "clients.html",
        clients=clients,
        client_totals=client_totals,
        countries=countries,
    )


# -------------------------
# DELETE CLIENT
# -------------------------
@main.route("/clients/delete/<int:id>")
def delete_client(id):
    client = CLIENT.query.get(id)
    if client:
        db.session.delete(client)
        db.session.commit()

    return redirect(url_for("main.clients"))


# -------------------------
# SUPPLIERS
# -------------------------
@main.route("/suppliers")
def suppliers():
    return render_template("suppliers.html", suppliers=SUPPLIER.query.all())


# -------------------------
# WEBUSERS
# -------------------------
@main.route("/webusers")
def webusers():
    return render_template("webusers.html", webusers=WEBUSER.query.all())


# -------------------------
# PRODUCTS
# -------------------------
@main.route("/products")
def products():

    rows = (
        db.session.query(PRODUCT, BRAND)
        .outerjoin(BRAND, PRODUCT.BRAND_ID == BRAND.BRAND_ID)
        .all()
    )

    return render_template("products.html", products=rows)


# -------------------------
# ORDERS
# -------------------------
@main.route("/orders")
def orders():
    rows = (
        db.session.query(
            ORDER_LINE.ORDER_LINE_NR,
            ORDER_LINE.ORDER_NR,
            ORDER.CLIENT_ID,
            ORDER.SUPPLIER_ID,
            ORDER_LINE.PRODUCT_ID,
            ORDER_LINE.Quantity,
            ORDER_LINE.Paid_price,
            ORDER_LINE.Currency,
            ORDER.Order_date,
        )
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .all()
    )

    return render_template("orders.html", order_rows=rows)


# -------------------------
# COSTS PAGE
# -------------------------
@main.route("/costs")
def costs():
    return render_template("costs.html")




