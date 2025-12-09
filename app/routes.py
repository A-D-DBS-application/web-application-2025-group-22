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
    client_count = CLIENT.query.count()
    product_count = PRODUCT.query.count()
    order_count = ORDER.query.count()
    webuser_count = WEBUSER.query.count()
    supplier_count = SUPPLIER.query.count()

    # Haal de 5 meest recente orders op
    recent_orders = ORDER.query.order_by(ORDER.Order_date.desc()).limit(5).all()


    return render_template(
        "home.html",
        client_count=client_count,
        product_count=product_count,
        order_count=order_count,
        webuser_count=webuser_count,
        supplier_count=supplier_count,
        recent_orders=recent_orders   
    )



# -------------------------
# MARGIN PAGE
# -------------------------
@main.route("/margin")
def margin_page():
    """
    NET MARGIN ANALYSIS

    Revenue per order:
      - ORDER.Paid_price

    Net margin per order:
      ORDER.Paid_price
      - Σ(Production_cost * ORDER_LINE.Quantity)
      - Σ(Inbound_transport_cost * ORDER_LINE.Quantity)
      - Σ(Storage_cost * ORDER_LINE.Quantity)
      - ((CLIENT_COST.Outbound_transport_cost * ORDER.Quantity)
         / number_of_orders_for_that_client_in_selected_year)
      - (License_fee_procent * ORDER.Paid_price)
    """

    selected_year_str = request.args.get("year", "").strip()
    selected_country = request.args.get("country", "").strip()
    selected_client_id = request.args.get("client_id", type=int)
    selected_year = int(selected_year_str) if selected_year_str.isdigit() else None

    # -------------------------
    # COUNTRY LIST
    # -------------------------
    countries = sorted({c.Country for c in CLIENT.query.all() if c.Country})

    # -------------------------
    # YEAR LIST (distinct years with orders)
    # -------------------------
    year_rows = (
        db.session.query(func.extract("year", ORDER.Order_date).label("year"))
        .distinct()
        .order_by("year")
        .all()
    )
    years = [int(r.year) for r in year_rows if r.year is not None]

    # -------------------------
    # CLIENT LIST (optionally filtered by country)
    # -------------------------
    client_query = CLIENT.query
    if selected_country:
        country_norm = selected_country.lower()
        client_query = client_query.filter(
            func.lower(func.trim(CLIENT.Country)) == country_norm
        )

    clients = client_query.order_by(CLIENT.Name).all()

    avg_margin = None
    sum_margin = None
    order_count = 0
    orders_for_view: list[dict] = []

    # Geen jaar gekozen → enkel filters tonen
    if not selected_year:
        return render_template(
            "margin.html",
            avg_margin=avg_margin,
            sum_margin=sum_margin,
            order_count=order_count,
            orders=orders_for_view,
            countries=countries,
            clients=clients,
            years=years,
            selected_year=selected_year,
            selected_country=selected_country,
            selected_client_id=selected_client_id,
        )

    # -------------------------
    # BASE FILTERS (year + optional country)
    # -------------------------
    start_date = date(selected_year, 1, 1)
    end_date = date(selected_year, 12, 31)

    base_filters_year_country = [
        ORDER.Order_date >= start_date,
        ORDER.Order_date <= end_date,
    ]
    if selected_country:
        country_norm = selected_country.lower()
        base_filters_year_country.append(
            func.lower(func.trim(CLIENT.Country)) == country_norm
        )

    # -------------------------
    # COST TERMS (COALESCE)
    # -------------------------
    inbound = func.coalesce(PRODUCT_COST.Inbound_transport_cost, 0.0)
    prod_cost = func.coalesce(PRODUCT_COST.Production_cost, 0.0)
    storage = func.coalesce(PRODUCT_COST.Storage_cost, 0.0)
    outbound = func.coalesce(CLIENT_COST.Outbound_transport_cost, 0.0)
    license_pct = func.coalesce(BRAND.License_fee_procent, 0.0)
    license_pct_effective = license_pct  # hier ga je er van uit dat dit al als fractie komt (bv. 0.15 voor 15%)

    # Revenue per order
    revenue_expr_order = func.coalesce(ORDER.Paid_price, 0.0)

    # --------------------------------------------------------
    # MODE 1 — CLIENT SELECTED
    # --------------------------------------------------------
    if selected_client_id:
        base_filters_client = list(base_filters_year_country)
        base_filters_client.append(ORDER.CLIENT_ID == selected_client_id)

        # aantal orders voor deze client in dit jaar
        order_count_value = (
            db.session.query(func.count(func.distinct(ORDER.ORDER_NR)))
            .join(CLIENT, CLIENT.CLIENT_ID == ORDER.CLIENT_ID)
            .filter(*base_filters_client)
            .scalar()
        )

        if not order_count_value:
            return render_template(
                "margin.html",
                avg_margin=0.0,
                sum_margin=0.0,
                order_count=0,
                orders=[],
                countries=countries,
                clients=clients,
                years=years,
                selected_year=selected_year,
                selected_country=selected_country,
                selected_client_id=selected_client_id,
            )

        orders_per_client_const = float(order_count_value)

        # LET OP: inbound nu per ORDER_LINE.Quantity (per product), niet meer per ORDER.Quantity
        prod_sum_expr = func.sum(prod_cost * ORDER_LINE.Quantity)
        inbound_sum_expr = func.sum(inbound * ORDER_LINE.Quantity)
        storage_sum_expr = func.sum(storage * ORDER_LINE.Quantity)
        outbound_sum_expr = func.sum((outbound * ORDER.Quantity) / orders_per_client_const)
        license_amount_expr = func.max(license_pct_effective) * revenue_expr_order
        total_qty_expr = func.sum(ORDER_LINE.Quantity)

        order_margin_expr = (
            revenue_expr_order
            - prod_sum_expr
            - inbound_sum_expr
            - storage_sum_expr
            - outbound_sum_expr
            - license_amount_expr
        )

        per_order_query = (
            db.session.query(
                ORDER.ORDER_NR.label("order_nr"),
                ORDER.Order_date.label("order_date"),
                revenue_expr_order.label("revenue"),
                prod_sum_expr.label("prod_sum"),
                inbound_sum_expr.label("inbound_sum"),
                storage_sum_expr.label("storage_sum"),
                outbound_sum_expr.label("outbound_sum"),
                license_amount_expr.label("license_amount"),
                order_margin_expr.label("order_margin"),
                total_qty_expr.label("total_quantity"),
            )
            .select_from(ORDER_LINE)
            .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
            .join(PRODUCT, ORDER_LINE.PRODUCT_ID == PRODUCT.PRODUCT_ID)
            .join(PRODUCT_COST, PRODUCT.PRODUCT_ID == PRODUCT_COST.PRODUCT_ID)
            .join(BRAND, PRODUCT.BRAND_ID == BRAND.BRAND_ID)
            .join(CLIENT, ORDER.CLIENT_ID == CLIENT.CLIENT_ID)
            .outerjoin(CLIENT_COST, CLIENT_COST.CLIENT_ID == CLIENT.CLIENT_ID)
            .filter(*base_filters_client)
            .group_by(ORDER.ORDER_NR, ORDER.Order_date, ORDER.Paid_price)
            .order_by(ORDER.Order_date.asc())
        )

        per_order_rows = per_order_query.all()

    # --------------------------------------------------------
    # MODE 2 — NO CLIENT SELECTED
    # --------------------------------------------------------
    else:
        # subquery: aantal orders per client in dit jaar (en optioneel land)
        order_count_subq = (
            db.session.query(
                ORDER.CLIENT_ID.label("CLIENT_ID"),
                func.count(func.distinct(ORDER.ORDER_NR)).label("order_count"),
            )
            .join(CLIENT, CLIENT.CLIENT_ID == ORDER.CLIENT_ID)
            .filter(*base_filters_year_country)
            .group_by(ORDER.CLIENT_ID)
            .subquery()
        )

        orders_per_client = func.nullif(order_count_subq.c.order_count, 0.0)

        # ook hier: inbound per ORDER_LINE.Quantity
        prod_sum_expr = func.sum(prod_cost * ORDER_LINE.Quantity)
        inbound_sum_expr = func.sum(inbound * ORDER_LINE.Quantity)
        storage_sum_expr = func.sum(storage * ORDER_LINE.Quantity)
        outbound_sum_expr = func.sum((outbound * ORDER.Quantity) / orders_per_client)
        license_amount_expr = func.max(license_pct_effective) * revenue_expr_order
        total_qty_expr = func.sum(ORDER_LINE.Quantity)

        order_margin_expr = (
            revenue_expr_order
            - prod_sum_expr
            - inbound_sum_expr
            - storage_sum_expr
            - outbound_sum_expr
            - license_amount_expr
        )

        per_order_query = (
            db.session.query(
                ORDER.ORDER_NR.label("order_nr"),
                ORDER.Order_date.label("order_date"),
                revenue_expr_order.label("revenue"),
                prod_sum_expr.label("prod_sum"),
                inbound_sum_expr.label("inbound_sum"),
                storage_sum_expr.label("storage_sum"),
                outbound_sum_expr.label("outbound_sum"),
                license_amount_expr.label("license_amount"),
                order_margin_expr.label("order_margin"),
                total_qty_expr.label("total_quantity"),
                func.max(order_count_subq.c.order_count).label("orders_per_client"),
            )
            .select_from(ORDER_LINE)
            .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
            .join(PRODUCT, ORDER_LINE.PRODUCT_ID == PRODUCT.PRODUCT_ID)
            .join(PRODUCT_COST, PRODUCT.PRODUCT_ID == PRODUCT_COST.PRODUCT_ID)
            .join(BRAND, PRODUCT.BRAND_ID == BRAND.BRAND_ID)
            .join(CLIENT, ORDER.CLIENT_ID == CLIENT.CLIENT_ID)
            .outerjoin(CLIENT_COST, CLIENT_COST.CLIENT_ID == CLIENT.CLIENT_ID)
            .outerjoin(order_count_subq, order_count_subq.c.CLIENT_ID == ORDER.CLIENT_ID)
            .filter(*base_filters_year_country)
            .group_by(ORDER.ORDER_NR, ORDER.Order_date, ORDER.Paid_price)
            .order_by(ORDER.Order_date.asc())
        )

        per_order_rows = per_order_query.all()

    # -------------------------
    # GEEN ORDERS?
    # -------------------------
    if not per_order_rows:
        return render_template(
            "margin.html",
            avg_margin=0.0,
            sum_margin=0.0,
            order_count=0,
            orders=[],
            countries=countries,
            clients=clients,
            years=years,
            selected_year=selected_year,
            selected_country=selected_country,
            selected_client_id=selected_client_id,
        )

    # -------------------------
    # PREP DATA FOR TEMPLATE
    # -------------------------
    sum_margins = 0.0
    orders_for_view = []

    for r in per_order_rows:
        margin_value = float(r.order_margin or 0.0)
        revenue_value = float(r.revenue or 0.0)

        prod_sum = float(r.prod_sum or 0.0)
        inbound_sum = float(r.inbound_sum or 0.0)
        storage_sum = float(r.storage_sum or 0.0)
        outbound_sum = float(r.outbound_sum or 0.0)
        license_amount = float(r.license_amount or 0.0)
        total_qty = float(r.total_quantity or 0.0)

        sum_margins += margin_value
        date_str = r.order_date.strftime("%Y-%m-%d") if r.order_date else ""

        margin_pct = None
        if revenue_value:
            margin_pct = round((margin_value / revenue_value) * 100.0, 2)

        if selected_client_id:
            opc = order_count_value
        else:
            opc = int(r.orders_per_client or 0) if hasattr(r, "orders_per_client") else 0

        orders_for_view.append(
            {
                "order_nr": r.order_nr,
                "order_date": date_str,
                "revenue": round(revenue_value, 2),
                "order_margin": round(margin_value, 2),
                "margin_pct": margin_pct,
                "prod_sum": round(prod_sum, 2),
                "inbound_sum": round(inbound_sum, 2),
                "storage_sum": round(storage_sum, 2),
                "outbound_sum": round(outbound_sum, 2),
                "license_amount": round(license_amount, 2),
                "orders_per_client": opc,
                "total_quantity": total_qty,
            }
        )

    order_count = len(per_order_rows)
    avg_margin = round(sum_margins / order_count, 2)
    sum_margin = round(sum_margins, 2)

    return render_template(
        "margin.html",
        avg_margin=avg_margin,
        sum_margin=sum_margin,
        order_count=order_count,
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

    # Basis query
    query = CLIENT.query

    if name:
        query = query.filter(func.lower(CLIENT.Name).like(f"%{name}%"))

    if country:
        query = query.filter(func.lower(CLIENT.Country) == country)

    clients = query.all()

    # Dictionary voor totals
    client_totals = {
        c.CLIENT_ID: {
            "total_revenue": 0,
            "total_production_cost": 0,
            "total_transport_cost": 0,
            "total_storage_cost": 0,
        }
        for c in clients
    }

    client_ids = [c.CLIENT_ID for c in clients]

    # ---------------- REVENUE ----------------
    revenue_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER.Paid_price).label("total_revenue")
        )
        .filter(ORDER.CLIENT_ID.in_(client_ids))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in revenue_rows:
        client_totals[row.CLIENT_ID]["total_revenue"] = float(row.total_revenue or 0)

    # ---------------- PRODUCTION COST ----------------
    production_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(ORDER_LINE.Quantity * PRODUCT_COST.Production_cost).label("total_production_cost")
        )
        .select_from(ORDER_LINE)                                            # FIX
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT_COST, PRODUCT_COST.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .filter(ORDER.CLIENT_ID.in_(client_ids))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in production_rows:
        client_totals[row.CLIENT_ID]["total_production_cost"] = float(row.total_production_cost or 0)

    # ---------------- TRANSPORT COST ----------------
    transport_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(PRODUCT_COST.Inbound_transport_cost * ORDER_LINE.Quantity).label("total_transport_cost")
        )
        .select_from(ORDER_LINE)                                           # FIX
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT_COST, PRODUCT_COST.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .filter(ORDER.CLIENT_ID.in_(client_ids))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in transport_rows:
        client_totals[row.CLIENT_ID]["total_transport_cost"] = float(row.total_transport_cost or 0)

    # ---------------- STORAGE COST ----------------
    storage_rows = (
        db.session.query(
            ORDER.CLIENT_ID,
            func.sum(PRODUCT_COST.Storage_cost * ORDER_LINE.Quantity).label("total_storage_cost")
        )
        .select_from(ORDER_LINE)                                          # FIX
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT_COST, PRODUCT_COST.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .filter(ORDER.CLIENT_ID.in_(client_ids))
        .group_by(ORDER.CLIENT_ID)
        .all()
    )

    for row in storage_rows:
        client_totals[row.CLIENT_ID]["total_storage_cost"] = float(row.total_storage_cost or 0)

    # ---------------- FILTEREN ----------------
    if min_rev:
        clients = [c for c in clients if client_totals[c.CLIENT_ID]["total_revenue"] >= float(min_rev)]
    if max_rev:
        clients = [c for c in clients if client_totals[c.CLIENT_ID]["total_revenue"] <= float(max_rev)]

    # ---------------- SORTEREN ----------------
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

    # Basisselectie
    query = (
        db.session.query(
            ORDER_LINE.ORDER_LINE_NR,
            ORDER_LINE.ORDER_NR,
            ORDER.CLIENT_ID,
            CLIENT.Name.label("ClientName"),
            SUPPLIER.Name.label("SupplierName"),
            PRODUCT.Name.label("ProductName"),
            ORDER_LINE.Quantity,
            PRODUCT.Sell_price_per_product.label("Unit_price"),
            PRODUCT.Currency.label("Currency"),
            ORDER.Order_date,
            ORDER.Paid_price.label("OrderPaidPrice")
        )
        .select_from(ORDER_LINE)
        .join(ORDER, ORDER_LINE.ORDER_NR == ORDER.ORDER_NR)
        .join(PRODUCT, PRODUCT.PRODUCT_ID == ORDER_LINE.PRODUCT_ID)
        .join(CLIENT, CLIENT.CLIENT_ID == ORDER.CLIENT_ID)
        .join(SUPPLIER, SUPPLIER.SUPPLIER_ID == ORDER.SUPPLIER_ID)
    )

    # -------- FILTERS --------
    if min_q is not None:
        query = query.filter(ORDER_LINE.Quantity >= min_q)

    if max_q is not None:
        query = query.filter(ORDER_LINE.Quantity <= max_q)

    if product_id is not None:
        query = query.filter(ORDER_LINE.PRODUCT_ID == product_id)

    if client_id is not None:
        query = query.filter(ORDER.CLIENT_ID == client_id)

    # -------- SORTEREN --------
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
    else:
        query = query.order_by(ORDER_LINE.ORDER_LINE_NR.asc())

    rows = query.all()

    return render_template("orders.html", order_rows=rows)


# -------------------------
# FORECAST REVENUE (SES — beste voor startups)
# -------------------------
@main.route("/forecast")
def forecast_page():
    from sqlalchemy import func

    # 1. Revenue per maand ophalen (som van ORDER.Paid_price)
    results = (
        db.session.query(
            func.to_char(ORDER.Order_date, "YYYY-MM").label("month"),
            func.sum(ORDER.Paid_price).label("revenue"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    if not results:
        return render_template(
            "forecast.html",
            labels=[],
            history_data=[],
            forecast_data=[],
            table_rows=[],
            alpha_used=None,
            method_info="Geen data beschikbaar om een forecast te maken.",
        )

    # 2. Data omzetten naar Python-lijsten
    labels = [row.month for row in results]
    history_data = [float(row.revenue or 0.0) for row in results]

    # 3. Simple Exponential Smoothing (SES) zonder extra libraries
    alpha = 0.4  # midden in jouw gewenste range 0.3–0.5

    forecast_data = []
    level = None

    for value in history_data:
        if level is None:
            # eerste maand: geen forecast, enkel initialisatie
            forecast_data.append(None)
            level = value
        else:
            # forecast voor huidige maand = vorige level
            forecast_data.append(level)
            # update level met SES-formule
            level = alpha * value + (1 - alpha) * level

    # 4. Tabel-rows bouwen
    table_rows = []
    for month, actual, fc in zip(labels, history_data, forecast_data):
        table_rows.append(
            {
                "month": month,
                "historical": round(actual, 2),
                "forecast": None if fc is None else round(fc, 2),
            }
        )

    method_info = (
        "We gebruiken Simple Exponential Smoothing (zonder seasonality) "
        "omdat de start-up nog geen stabiele seizoenspatronen heeft. "
        "Een α-waarde rond 0.3–0.5 laat het model snel genoeg reageren "
        "op veranderende vraag in jonge, onstabiele datasets."
    )

    return render_template(
        "forecast.html",
        labels=labels,
        history_data=history_data,
        forecast_data=forecast_data,
        table_rows=table_rows,
        alpha_used=alpha,
        method_info=method_info,
    )


# -------------------------
# COSTS PAGE
# -------------------------
@main.route("/costs")
def costs():
    return render_template("costs.html")



# -------------------------
# ADD RECORDS - OVERZICHT
# -------------------------
@main.route("/add-records", methods=["GET"])
def add_records_page():
    """
    Pagina om nieuwe records toe te voegen aan de belangrijkste tabellen:
    - CLIENT
    - BRAND
    - PRODUCT
    - ORDER (alleen als de client bestaat)
    """

    clients = CLIENT.query.order_by(CLIENT.Name).all()
    suppliers = SUPPLIER.query.order_by(SUPPLIER.Name).all()
    brands = BRAND.query.order_by(BRAND.Name).all()
    products = PRODUCT.query.order_by(PRODUCT.Name).all()

    return render_template(
        "add_records.html",
        clients=clients,
        suppliers=suppliers,
        brands=brands,
        products=products,
    )


# -------------------------
# ADD CLIENT
# -------------------------
@main.route("/add-record/client", methods=["POST"])
def add_record_client():
    name = request.form.get("name")
    country = request.form.get("country")
    postal = request.form.get("postal_code")
    city = request.form.get("city")
    street = request.form.get("street")
    house = request.form.get("house_number")
    btw_vat = request.form.get("btw_vat")
    email = request.form.get("email")

    if not name:
        return redirect(url_for("main.add_records_page"))

    new_client = CLIENT(
        Name=name,
        Country=country,
        Postal_code=postal,
        City=city,
        Street=street,
        House_number=house,
        BTW_VAT=btw_vat,
        Email=email,
    )
    db.session.add(new_client)
    db.session.commit()

    return redirect(url_for("main.add_records_page"))


# -------------------------
# ADD BRAND
# -------------------------
@main.route("/add-record/brand", methods=["POST"])
def add_record_brand():
    name = request.form.get("name")
    license_fee = request.form.get("license_fee")
    supplier_id = request.form.get("supplier_id", type=int)

    if not name or not supplier_id:
        return redirect(url_for("main.add_records_page"))

    supplier = SUPPLIER.query.get(supplier_id)
    if not supplier:
        return redirect(url_for("main.add_records_page"))

    try:
        license_fee_value = float(license_fee) if license_fee else 0.0
    except ValueError:
        license_fee_value = 0.0

    new_brand = BRAND(
        Name=name,
        License_fee_procent=license_fee_value,
        SUPPLIER_ID=supplier_id,
    )
    db.session.add(new_brand)
    db.session.commit()

    return redirect(url_for("main.add_records_page"))


# -------------------------
# ADD PRODUCT
# -------------------------
@main.route("/add-record/product", methods=["POST"])
def add_record_product():
    name = request.form.get("name")
    brand_id = request.form.get("brand_id", type=int)
    supplier_id = request.form.get("supplier_id", type=int)
    sell_price = request.form.get("sell_price")
    currency = request.form.get("currency")

    if not name or not brand_id or not supplier_id:
        return redirect(url_for("main.add_records_page"))

    try:
        sell_price_value = float(sell_price) if sell_price else 0.0
    except ValueError:
        sell_price_value = 0.0

    if not BRAND.query.get(brand_id) or not SUPPLIER.query.get(supplier_id):
        return redirect(url_for("main.add_records_page"))

    new_product = PRODUCT(
        Name=name,
        BRAND_ID=brand_id,
        SUPPLIER_ID=supplier_id,
        Sell_price_per_product=sell_price_value,
        Currency=currency or "EUR",
    )
    db.session.add(new_product)
    db.session.commit()

    return redirect(url_for("main.add_records_page"))


# -------------------------
# HELPERS: ORDER_NR GENEREREN
# -------------------------
def generate_next_order_nr(order_date: date) -> str:
    """
    ORDER_NR-formaat: 'YYYY-N'.
    We zoeken alle orders die starten met 'YYYY-' en nemen de hoogste N, +1.
    """
    year = order_date.year
    prefix = f"{year}-"

    existing_orders = ORDER.query.filter(ORDER.ORDER_NR.like(f"{prefix}%")).all()

    max_n = 0
    for o in existing_orders:
        try:
            part = o.ORDER_NR.split("-")[1]
            n = int(part)
            if n > max_n:
                max_n = n
        except (IndexError, ValueError):
            continue

    next_n = max_n + 1
    return f"{year}-{next_n}"


# -------------------------
# ADD ORDER (ENKEL ALS CLIENT BESTAAT)
# -------------------------
@main.route("/add-record/order", methods=["POST"])
def add_record_order():
    client_id = request.form.get("client_id", type=int)
    supplier_id = request.form.get("supplier_id", type=int)
    order_date_str = request.form.get("order_date")
    status = request.form.get("status") or "Deliverd"
    quantity = request.form.get("quantity", type=int)
    paid_price = request.form.get("paid_price")

    if not client_id or not supplier_id or not order_date_str:
        return redirect(url_for("main.add_records_page"))

    # Client moet bestaan
    client = CLIENT.query.get(client_id)
    if not client:
        return redirect(url_for("main.add_records_page"))

    supplier = SUPPLIER.query.get(supplier_id)
    if not supplier:
        return redirect(url_for("main.add_records_page"))

    try:
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for("main.add_records_page"))

    try:
        paid_price_value = float(paid_price) if paid_price else 0.0
    except ValueError:
        paid_price_value = 0.0

    # Automatisch volgend ORDER_NR
    new_order_nr = generate_next_order_nr(order_date)

    new_order = ORDER(
        ORDER_NR=new_order_nr,
        CLIENT_ID=client_id,
        SUPPLIER_ID=supplier_id,
        Order_date=order_date,
        Status=status,
        Quantity=quantity or 0,
        Paid_price=paid_price_value,
    )

    db.session.add(new_order)
    db.session.commit()

    return redirect(url_for("main.add_records_page"))

