from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import func
from datetime import datetime
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

        user.Last_seen = datetime.now()
        db.session.commit()

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

    name = request.args.get("name", "").strip().lower()
    country = request.args.get("country", "").strip().lower()
    min_rev = request.args.get("min_rev", "")
    max_rev = request.args.get("max_rev", "")
    sort = request.args.get("sort", "default")

    query = CLIENT.query

    if name:
        query = query.filter(func.lower(CLIENT.Name).like(f"%{name}%"))

    if country:
        query = query.filter(func.lower(CLIENT.Country) == country)

    clients = query.all()

    client_totals = {
        c.CLIENT_ID: {
            "total_revenue": 0,
            "total_production_cost": 0,
            "total_transport_cost": 0,
            "total_storage_cost": 0,
        }
        for c in clients
    }

    revenue_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER_LINE.Paid_price).label("total_revenue")
        )
        .join(ORDER_LINE, ORDER.ORDER_NR == ORDER_LINE.ORDER_NR)
        .filter(ORDER.CLIENT_ID.in_([c.CLIENT_ID for c in clients]))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )
    for row in revenue_rows:
        client_totals[row.CLIENT_ID]["total_revenue"] = float(row.total_revenue or 0)

    production_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER_LINE.Quantity * PRODUCT_COST.Production_cost).label("total_production_cost")
        )
        .join(ORDER_LINE, ORDER.ORDER_NR == ORDER_LINE.ORDER_NR)
        .join(PRODUCT, PRODUCT.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .join(PRODUCT_COST, PRODUCT_COST.PRODUCT_ID == PRODUCT.PRODUCT_ID)
        .filter(ORDER.CLIENT_ID.in_([c.CLIENT_ID for c in clients]))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )
    for row in production_rows:
        client_totals[row.CLIENT_ID]["total_production_cost"] = float(row.total_production_cost or 0)

    if min_rev:
        clients = [c for c in clients if client_totals[c.CLIENT_ID]["total_revenue"] >= float(min_rev)]
    if max_rev:
        clients = [c for c in clients if client_totals[c.CLIENT_ID]["total_revenue"] <= float(max_rev)]

    if sort == "name-asc":
        clients = sorted(clients, key=lambda c: c.Name.lower())
    elif sort == "name-desc":
        clients = sorted(clients, key=lambda c: c.Name.lower(), reverse=True)
    elif sort == "rev-asc":
        clients = sorted(clients, key=lambda c: client_totals[c.CLIENT_ID]["total_revenue"])
    elif sort == "rev-desc":
        clients = sorted(clients, key=lambda c: client_totals[c.CLIENT_ID]["total_revenue"], reverse=True)

    countries = sorted({c.Country for c in CLIENT.query.all()})

    return render_template(
        "clients.html",
        clients=clients,
        client_totals=client_totals,
        countries=countries,
        request_args=request.args
    )


# -------------------------
# ADD CLIENT
# -------------------------
@main.route("/clients/add", methods=["POST"])
def add_client():
    name = request.form.get("name")
    country = request.form.get("country")
    postal = request.form.get("postal_code")
    city = request.form.get("city")
    street = request.form.get("street")
    house = request.form.get("house_number")

    if not name or not country:
        return redirect(url_for("main.clients"))

    new_client = CLIENT(
        Name=name,
        Country=country,
        Postal_code=postal,
        City=city,
        Street=street,
        House_number=house
    )

    db.session.add(new_client)
    db.session.commit()

    return redirect(url_for("main.clients"))


# -------------------------
# DELETE CLIENT BY NAME
# -------------------------
@main.route("/clients/delete_by_name", methods=["POST"])
def delete_client_by_name():
    name = request.form.get("name")

    if not name:
        return redirect(url_for("main.clients"))

    client = CLIENT.query.filter(func.lower(CLIENT.Name) == name.lower()).first()

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
        db.session.query(PRODUCT, BRAND, PRODUCT_COST)
        .outerjoin(BRAND, PRODUCT.BRAND_ID == BRAND.BRAND_ID)
        .outerjoin(PRODUCT_COST, PRODUCT.PRODUCT_ID == PRODUCT_COST.PRODUCT_ID)
        .all()
    )

    return render_template("products.html", products=rows)


# -------------------------
# ORDERS
# -------------------------
@main.route("/orders")
def orders():

    sort = request.args.get("sort", "")
    min_q = request.args.get("min_q", type=int)
    max_q = request.args.get("max_q", type=int)
    product_id = request.args.get("product_id", type=int)
    client_id = request.args.get("client_id", type=int)

    query = (
        db.session.query(
            ORDER_LINE.ORDER_LINE_NR,
            ORDER_LINE.ORDER_NR,
            ORDER.CLIENT_ID,
            ORDER.SUPPLIER_ID,
            ORDER_LINE.PRODUCT_ID.label("PRODUCT_ID"),
            ORDER_LINE.Quantity,
            PRODUCT.Sell_price_per_product.label("Unit_price"),
            ORDER_LINE.Currency,
            ORDER.Order_date
        )
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT, PRODUCT.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
    )

    if min_q is not None:
        query = query.filter(ORDER_LINE.Quantity >= min_q)

    if max_q is not None:
        query = query.filter(ORDER_LINE.Quantity <= max_q)

    if product_id is not None:
        query = query.filter(ORDER_LINE.PRODUCT_ID == product_id)

    if client_id is not None:
        query = query.filter(ORDER.CLIENT_ID == client_id)

    if sort == "quantity-asc":
        query = query.order_by(ORDER_LINE.Quantity.asc())
    elif sort == "quantity-desc":
        query = query.order_by(ORDER_LINE.Quantity.desc())
    elif sort == "date-asc":
        query = query.order_by(ORDER.Order_date.asc())
    elif sort == "date-desc":
        query = query.order_by(ORDER.Order_date.desc())
    elif sort == "price-asc":
        query = query.order_by(PRODUCT.Sell_price_per_product.asc())
    elif sort == "price-desc":
        query = query.order_by(PRODUCT.Sell_price_per_product.desc())

    rows = query.all()

    return render_template("orders.html", order_rows=rows)


# -------------------------
# COSTS
# -------------------------
@main.route("/costs")
def costs():
    return render_template("costs.html")






