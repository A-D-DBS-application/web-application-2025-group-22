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
    PRODUCT_COST,
    CLIENT_COST,
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
# MARGIN PAGE
# -------------------------
@main.route("/margin")
def margin_page():
    """
    MARGE PER KLANT (filterbaar per jaar)

    - MARGE PER ORDER:
      Omzet = ORDER.Paid_price  (totaal betaalde prijs voor de order)

      Nettomarge per order =

      ORDER.Paid_price
      - som_per_product( PRODUCT_COST.Production_cost * ORDER_LINE.Quantity )
      - som_per_product( PRODUCT_COST.Inbound_transport_cost * ORDER.Quantity )
      - som_per_product( PRODUCT_COST.Storage_cost * ORDER_LINE.Quantity )
      - som_per_product( (CLIENT_COST.Outbound_transport_cost * ORDER.Quantity)
                         / aantal_orders_klant_in_het_gekozen_jaar )
      - ( License_fee_procent * ORDER.Paid_price )

    - MARGE PER KLANT:
      GEMIDDELDE van alle nettomarges van de orders van die specifieke klant
      in het gekozen jaar.
    """

    # -------------------------
    # FILTERPARAMS UIT QUERYSTRING
    # -------------------------
    selected_year_str = request.args.get("year", "").strip()
    selected_country = request.args.get("country", "").strip()
    selected_client_id = request.args.get("client_id", type=int)

    # year -> int / None
    selected_year = int(selected_year_str) if selected_year_str.isdigit() else None

    # -------------------------
    # LANDEN-LIJST (voor dropdown)
    # -------------------------
    countries = sorted({c.Country for c in CLIENT.query.all() if c.Country})

    # -------------------------
    # JAAR-LIJST (distinct jaren met orders)
    # -------------------------
    year_rows = (
        db.session.query(func.extract("year", ORDER.Order_date).label("year"))
        .distinct()
        .order_by("year")
        .all()
    )
    years = [int(r.year) for r in year_rows if r.year is not None]

    # -------------------------
    # CLIENT-LIJST gefilterd op land
    # -------------------------
    client_query = CLIENT.query
    if selected_country:
        country_norm = selected_country.lower()
        client_query = client_query.filter(
            func.lower(func.trim(CLIENT.Country)) == country_norm
        )

    clients = client_query.order_by(CLIENT.Name).all()

    # Default: nog niks berekend
    total_margin = None
    orders_for_view: list[dict] = []

    # Nog niet alles gekozen -> alleen filters tonen
    # We rekenen pas als én jaar én klant gekozen zijn.
    if not selected_client_id or not selected_year:
        return render_template(
            "margin.html",
            total_margin=total_margin,
            orders=orders_for_view,
            countries=countries,
            clients=clients,
            years=years,
            selected_year=selected_year,
            selected_country=selected_country,
            selected_client_id=selected_client_id,
        )

    # -------------------------
    # BASISFILTERS (gekozen jaar + klant [+ optioneel land])
    # -------------------------
    start_date = date(selected_year, 1, 1)
    end_date = date(selected_year, 12, 31)

    base_filters = [
        ORDER.Order_date >= start_date,
        ORDER.Order_date <= end_date,
        ORDER.CLIENT_ID == selected_client_id,
    ]
    if selected_country:
        country_norm = selected_country.lower()
        base_filters.append(
            func.lower(func.trim(CLIENT.Country)) == country_norm
        )

    # -------------------------
    # AANTAL ORDERS VAN DEZE KLANT IN DIT JAAR
    # -------------------------
    order_count_value = (
        db.session.query(func.count(func.distinct(ORDER.ORDER_NR)))
        .join(CLIENT, CLIENT.CLIENT_ID == ORDER.CLIENT_ID)
        .filter(*base_filters)
        .scalar()
    )

    if not order_count_value:
        # Geen orders: marge 0 en lege tabel
        total_margin = 0.0
        return render_template(
            "margin.html",
            total_margin=total_margin,
            orders=orders_for_view,
            countries=countries,
            clients=clients,
            years=years,
            selected_year=selected_year,
            selected_country=selected_country,
            selected_client_id=selected_client_id,
        )

    orders_per_client_const = float(order_count_value)

    # -------------------------
    # KOSTEN MET COALESCE (NULL -> 0)
    # -------------------------
    inbound = func.coalesce(PRODUCT_COST.Inbound_transport_cost, 0.0)
    prod_cost = func.coalesce(PRODUCT_COST.Production_cost, 0.0)
    storage = func.coalesce(PRODUCT_COST.Storage_cost, 0.0)
    outbound = func.coalesce(CLIENT_COST.Outbound_transport_cost, 0.0)
    license_pct = func.coalesce(BRAND.License_fee_procent, 0.0)
    # Als License_fee_procent = 5 betekent 5%, dan eventueel: license_pct_effective = license_pct / 100.0
    license_pct_effective = license_pct

    # -------------------------
    # OMZET & KOSTEN-TERMEN
    # -------------------------

    # Omzet per order = totaal betaalde prijs
    revenue_expr_order = func.coalesce(ORDER.Paid_price, 0.0)

    # Kosten die per productregel worden opgebouwd, later gesommeerd per order
    line_cost_expr = (
        (prod_cost * ORDER_LINE.Quantity)
        + (inbound * ORDER.Quantity)
        + (storage * ORDER_LINE.Quantity)
        + ((outbound * ORDER.Quantity) / orders_per_client_const)
    )

    # -------------------------
    # PER ORDER:
    #   revenue = ORDER.Paid_price
    #   marge  = revenue
    #           - som(line_cost_expr)
    #           - (license_pct_order * revenue)
    #
    # waarbij license_pct_order = max(License_fee_procent) over de lijnen van die order
    # (gaat ervan uit dat alle producten in de order dezelfde fee hebben).
    # -------------------------
    per_order_query = (
        db.session.query(
            ORDER.ORDER_NR.label("order_nr"),
            ORDER.Order_date.label("order_date"),
            revenue_expr_order.label("revenue"),
            (
                revenue_expr_order
                - func.sum(line_cost_expr)
                - (func.max(license_pct_effective) * revenue_expr_order)
            ).label("order_margin"),
        )
        .select_from(ORDER_LINE)
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT, ORDER_LINE.PRODUCT_ID == PRODUCT.PRODUCT_ID)
        .join(PRODUCT_COST, PRODUCT.PRODUCT_ID == PRODUCT_COST.PRODUCT_ID)
        .join(BRAND, PRODUCT.BRAND_ID == BRAND.BRAND_ID)
        .join(CLIENT, ORDER.CLIENT_ID == CLIENT.CLIENT_ID)
        .outerjoin(CLIENT_COST, CLIENT_COST.CLIENT_ID == CLIENT.CLIENT_ID)
        .filter(*base_filters)
        .group_by(ORDER.ORDER_NR, ORDER.Order_date, ORDER.Paid_price)
        .order_by(ORDER.Order_date.asc())
    )

    order_rows = per_order_query.all()

    # -------------------------
    # DATA VOOR TEMPLATE
    # -------------------------
    sum_margins = 0.0
    orders_for_view = []

    for r in order_rows:
        margin_value = float(r.order_margin or 0.0)
        revenue_value = float(r.revenue or 0.0)
        sum_margins += margin_value

        date_str = ""
        if r.order_date:
            date_str = r.order_date.strftime("%Y-%m-%d")

        orders_for_view.append({
            "order_nr": r.order_nr,
            "order_date": date_str,
            "revenue": round(revenue_value, 2),
            "order_margin": round(margin_value, 2),
        })

    if orders_per_client_const:
        avg_margin = sum_margins / orders_per_client_const
    else:
        avg_margin = 0.0

    total_margin = round(avg_margin, 2)

    return render_template(
        "margin.html",
        total_margin=total_margin,
        orders=orders_for_view,
        countries=countries,
        clients=clients,
        years=years,
        selected_year=selected_year,
        selected_country=selected_country,
        selected_client_id=selected_client_id,
    )

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

    # Outlier correctie
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

    # Seasonal decomposition via CMA
    df["rev_centered"] = df["revenue"].rolling(window=12, center=True).mean()
    df["seasonal_ratio"] = df["revenue"] / df["rev_centered"]
    df["month_num"] = df["month"].str[-2:].astype(int)

    seasonal_factors = df.groupby("month_num")["seasonal_ratio"].mean()
    seasonal_factors = seasonal_factors / seasonal_factors.mean()

    df["seasonal_factor"] = df["month_num"].map(seasonal_factors)
    df["trend"] = df["revenue"] / df["seasonal_factor"]

    valid_trend = df["trend"].dropna()
    t = np.arange(len(valid_trend))
    slope, intercept = np.polyfit(t, valid_trend, 1)

    future_months = 12
    last_index = len(df) - 1

    forecast_trend = [
        intercept + slope * (last_index + i + 1)
        for i in range(future_months)
    ]

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

    labels = list(df["month"]) + forecast_months
    history_data = list(df["revenue"]) + [None] * len(forecast_values)
    forecast_data = [None] * len(df) + list(forecast_values)

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
