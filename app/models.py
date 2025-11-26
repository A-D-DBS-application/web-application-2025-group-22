from . import db

# ---------------- WEBUSER ----------------
class WEBUSER(db.Model):
    __tablename__ = 'WEBUSER'

    WEBUSER_id = db.Column(db.Integer, primary_key=True)
    SUPPLIER_id = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))
    Name = db.Column(db.String)
    Email = db.Column(db.String)
    Role = db.Column(db.String)

    supplier = db.relationship("SUPPLIER", backref="webusers")


# ---------------- CLIENT ----------------
class CLIENT(db.Model):
    __tablename__ = 'CLIENT'

    CLIENT_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String)
    Country = db.Column(db.String)
    Postal_code = db.Column(db.String)
    City = db.Column(db.String)
    Street = db.Column(db.String)
    House_number = db.Column(db.String)

    # BELANGRIJK: kolom heet BTW/VAT in Supabase
    BTW_VAT = db.Column("BTW/VAT", db.String)

    Email = db.Column(db.String)

    orders = db.relationship("ORDER", backref="client")



# ---------------- SUPPLIER ----------------
class SUPPLIER(db.Model):
    __tablename__ = 'SUPPLIER'

    SUPPLIER_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String)
    Country = db.Column(db.String)
    Postal_code = db.Column(db.String)
    City = db.Column(db.String)
    Street = db.Column(db.String)
    House_number = db.Column(db.String)

    # BELANGRIJK: echte kolomnaam is "BTW/VAT"
    BTW_VAT = db.Column("BTW/VAT", db.String)

    Email = db.Column(db.String)
    Phone = db.Column(db.String)

    brands = db.relationship("BRAND", backref="supplier")
    products = db.relationship("PRODUCT", backref="supplier")
    orders = db.relationship("ORDER", backref="supplier")



# ---------------- BRAND ----------------
class BRAND(db.Model):
    __tablename__ = 'BRAND'

    BRAND_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String)
    License_fee_procent = db.Column(db.Float)
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))

    products = db.relationship("PRODUCT", backref="brand")


# ---------------- PRODUCT ----------------
class PRODUCT(db.Model):
    __tablename__ = 'PRODUCT'

    PRODUCT_ID = db.Column(db.Integer, primary_key=True)
    BRAND_ID = db.Column(db.Integer, db.ForeignKey('BRAND.BRAND_ID'))
    Name = db.Column(db.String)
    Sell_price_per_product = db.Column(db.Integer)
    Currency = db.Column(db.String)
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))

    order_lines = db.relationship("ORDER_LINE", backref="product")
    costs = db.relationship("PRODUCT_COST", backref="product")


# ---------------- PRODUCT_COST ----------------
class PRODUCT_COST(db.Model):
    __tablename__ = 'PRODUCT_COST'

    PRODUCT_COST_ID = db.Column(db.Integer, primary_key=True)
    PRODUCT_ID = db.Column(db.Integer, db.ForeignKey('PRODUCT.PRODUCT_ID'))

    Production_cost = db.Column(db.Float)
    Inbound_transport_cost = db.Column(db.Float)
    Outbound_transport_cost = db.Column(db.Float)
    Raw_material_transport_cost = db.Column(db.Float)
    Storage_cost = db.Column(db.Float)
    Warehousing_picking_cost = db.Column(db.Float)


# ---------------- ORDER ----------------
class ORDER(db.Model):
    __tablename__ = 'ORDER'

    ORDER_NR = db.Column(db.String, primary_key=True)
    CLIENT_ID = db.Column(db.Integer, db.ForeignKey('CLIENT.CLIENT_ID'))
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))
    Order_date = db.Column(db.Date)
    Status = db.Column(db.String)

    order_lines = db.relationship("ORDER_LINE", backref="order")


# ---------------- ORDER_LINE ----------------
class ORDER_LINE(db.Model):
    __tablename__ = 'ORDER_LINE'

    ORDER_LINE_NR = db.Column(db.Integer, primary_key=True)
    Quantity = db.Column(db.Integer)
    Paid_price = db.Column(db.Float)
    PRODUCT_ID = db.Column(db.Integer, db.ForeignKey('PRODUCT.PRODUCT_ID'))
    ORDER_NR = db.Column(db.String, db.ForeignKey('ORDER.ORDER_NR'))
    Currency = db.Column(db.String)


