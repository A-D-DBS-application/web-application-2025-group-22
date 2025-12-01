from flask import Blueprint, render_template, request, redirect, url_for
from sqlalchemy import func
from datetime import datetime, date
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
            return render_template(
                "register.html",
                message="Vul alles in.",
                suppliers=SUPPLIER.query.all()
            )

        existing = WEBUSER.query.filter_by(Name=username).first()
        if existing:
            return render_template(
                "register.html",
                message="Gebruiker bestaat al.",
                suppliers=SUPPLIER.query.all()
            )

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
# SUPPLIERS LIST
# -------------------------
@main.route("/suppliers")
def suppliers():
    return render_template("suppliers.html", suppliers=SUPPLIER.query.all())


# -------------------------
# WEBUSERS LIST
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
# ORDERS (WITH SUPPLIER + PRODUCT NAMES)
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
            SUPPLIER.Name.label("SupplierName"),
            PRODUCT.Name.label("ProductName"),
            ORDER_LINE.Quantity,
            PRODUCT.Sell_price_per_product.label("Unit_price"),
            ORDER_LINE.Currency,
            ORDER.Order_date
        )
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT, PRODUCT.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .join(SUPPLIER, SUPPLIER.SUPPLIER_ID == ORDER.SUPPLIER_ID)
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
# FORECAST REVENUE (12 MONTHS, SEASONAL)
# -------------------------
@main.route("/forecast")
def forecast_page():
    from sqlalchemy import func
    import numpy as np
    import pandas as pd

    # 1️⃣ Revenue per maand ophalen (som Paid_price)
    results = (
        db.session.query(
            func.to_char(ORDER.Order_date, 'YYYY-MM').label("month"),
            func.sum(ORDER_LINE.Paid_price).label("revenue")
        )
        .join(ORDER_LINE, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .group_by("month")
        .order_by("month")
        .all()
    )

    df = pd.DataFrame(results, columns=["month", "revenue"]).dropna()

    # ----------------------
    # 2️⃣ Outlier Correctie (T1)
    # ----------------------
    df["log_rev"] = np.log(df["revenue"] + 1)

    mean = df["log_rev"].mean()
    std = df["log_rev"].std()
    z = (df["log_rev"] - mean) / std
    threshold = 1.8

    df["log_rev_wins"] = df["log_rev"].clip(mean - threshold * std,
                                            mean + threshold * std)
    df["rev_corrected"] = np.exp(df["log_rev_wins"]) - 1
    df["is_outlier"] = abs(z) > threshold

    df["revenue"] = df["rev_corrected"]

    # ----------------------
    # 3️⃣ Seasonal decomposition via CMA
    # ----------------------
    df["rev_centered"] = df["revenue"].rolling(window=12, center=True).mean()
    df["seasonal_ratio"] = df["revenue"] / df["rev_centered"]
    df["month_num"] = df["month"].str[-2:].astype(int)

    seasonal_factors = df.groupby("month_num")["seasonal_ratio"].mean()
    seasonal_factors = seasonal_factors / seasonal_factors.mean()

    df["seasonal_factor"] = df["month_num"].map(seasonal_factors)
    df["trend"] = df["revenue"] / df["seasonal_factor"]

    # Trend extrapolatie
    valid_trend = df["trend"].dropna()
    t = np.arange(len(valid_trend))
    slope, intercept = np.polyfit(t, valid_trend, 1)

    future_months = 12
    last_index = len(df) - 1

    forecast_trend = [
        intercept + slope * (last_index + i + 1)
        for i in range(future_months)
    ]

    # Future maanden genereren
    last_month_dt = pd.to_datetime(df["month"].iloc[-1] + "-01")

    forecast_months = [
        (last_month_dt + pd.DateOffset(months=i + 1)).strftime("%Y-%m")
        for i in range(future_months)
    ]

    forecast_values = []
    for i, fm in enumerate(forecast_months):
        m = int(fm[-2:])
        sf = float(seasonal_factors.loc[m])
        forecast_values.append(forecast_trend[i] * sf)

    # ----------------------
    # 4️⃣ GRAFIEK-ALIGN FIX
    # ----------------------

    # Historische labels + forecast labels samen
    labels = list(df["month"]) + forecast_months

    # History data krijgt nulls voor forecast periode
    history_data = list(df["revenue"]) + [None] * len(forecast_values)

    # Forecast data krijgt nulls voor historische periode
    forecast_data = [None] * len(df) + list(forecast_values)

    # ----------------------
    # 5️⃣ Tabellen
    # ----------------------

    outlier_table = [
        {
            "period": row.month,
            "original": round(float(rev), 2),
            "corrected": round(float(corr), 2),
            "outlier": "Ja" if row.is_outlier else "Nee"
        }
        for row, rev, corr in zip(df.itertuples(), df["revenue"], df["rev_corrected"])
    ]

    future_table = [
        {"period": forecast_months[i], "forecast": round(float(v), 2)}
        for i, v in enumerate(forecast_values)
    ]

    return render_template(
        "forecast.html",
        labels=labels,
        history_data=history_data,
        forecast_data=forecast_data,
        seasonal_factors=[
            {"month": m, "factor": round(float(f), 4)}
            for m, f in seasonal_factors.items()
        ],
        forecast_table=future_table,
        outlier_table=outlier_table
    )




# -------------------------
# COSTS PAGE
# -------------------------
@main.route("/costs")
def costs():
    return render_template("costs.html")










