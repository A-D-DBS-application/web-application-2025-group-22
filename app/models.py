from . import db
from datetime import datetime


# ---------------- WEBUSER ----------------
class WEBUSER(db.Model):
    __tablename__ = 'WEBUSER'

    WEBUSER_id = db.Column(db.Integer, primary_key=True)
    SUPPLIER_id = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))
    Name = db.Column(db.String)
    Email = db.Column(db.String)
    Role = db.Column(db.String)

    # Nieuw veld
    Last_seen = db.Column(db.DateTime, default=None)

    supplier = db.relationship("SUPPLIER", backref="webusers")

    def __repr__(self):
        return f"<WEBUSER {self.WEBUSER_id} - {self.Name}>"


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

    BTW_VAT = db.Column("BTW/VAT", db.String)
    Email = db.Column(db.String)
    Outbound_transport_cost = db.Column(db.Float)

    orders = db.relationship("ORDER", backref="client")

    def __repr__(self):
        return f"<CLIENT {self.CLIENT_ID} - {self.Name}>"


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

    BTW_VAT = db.Column("BTW/VAT", db.String)

    Email = db.Column(db.String)
    Phone = db.Column(db.String)

    brands = db.relationship("BRAND", backref="supplier")
    products = db.relationship("PRODUCT", backref="supplier")
    orders = db.relationship("ORDER", backref="supplier")

    def __repr__(self):
        return f"<SUPPLIER {self.SUPPLIER_ID} - {self.Name}>"


# ---------------- BRAND ----------------
class BRAND(db.Model):
    __tablename__ = 'BRAND'

    BRAND_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String)
    # let op: als dit 8 is voor 8%, moet je in de query /100 doen
    License_fee_procent = db.Column(db.Float)
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))

    products = db.relationship("PRODUCT", backref="brand")

    def __repr__(self):
        return f"<BRAND {self.BRAND_ID} - {self.Name}>"


# ---------------- PRODUCT ----------------
class PRODUCT(db.Model):
    __tablename__ = 'PRODUCT'

    PRODUCT_ID = db.Column(db.Integer, primary_key=True)
    BRAND_ID = db.Column(db.Integer, db.ForeignKey('BRAND.BRAND_ID'))
    Name = db.Column(db.String)
    Currency = db.Column(db.String)
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))

    order_lines = db.relationship("ORDER_LINE", backref="product")
    # één rij met kosten per product
    costs = db.relationship("PRODUCT_COST", backref="product", uselist=False)

    def __repr__(self):
        return f"<PRODUCT {self.PRODUCT_ID} - {self.Name}>"


# ---------------- PRODUCT_COST ----------------
class PRODUCT_COST(db.Model):
    __tablename__ = 'PRODUCT_COST'

    PRODUCT_COST_ID = db.Column(db.Integer, primary_key=True)
    PRODUCT_ID = db.Column(db.Integer, db.ForeignKey('PRODUCT.PRODUCT_ID'))

    Production_cost = db.Column(db.Float)
    Inbound_transport_cost = db.Column(db.Float)      # fabriek -> magazijn
    Storage_cost = db.Column(db.Float)                # stockage per product
    

    def __repr__(self):
        return f"<PRODUCT_COST {self.PRODUCT_COST_ID} product={self.PRODUCT_ID}>"


# ---------------- ORDER ----------------
class ORDER(db.Model):
    __tablename__ = 'ORDER'

    ORDER_NR = db.Column(db.String, primary_key=True)
    CLIENT_ID = db.Column(db.Integer, db.ForeignKey('CLIENT.CLIENT_ID'))
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'))
    Status = db.Column(db.String)
    Order_date = db.Column(db.Date)

    # totaal aantal stuks in deze bestelling (som ORDER_LINE.Quantity)
    Quantity = db.Column(db.Integer)

    # totaal betaalde prijs voor de volledige order (zoals in Excel)
    Paid_price = db.Column(db.Float)

    order_lines = db.relationship("ORDER_LINE", backref="order")

    def __repr__(self):
        return f"<ORDER {self.ORDER_NR} - client={self.CLIENT_ID}>"


# ---------------- ORDER_LINE ----------------
class ORDER_LINE(db.Model):
    __tablename__ = 'ORDER_LINE'

    ORDER_LINE_NR = db.Column(db.Integer, primary_key=True)
    ORDER_NR = db.Column(db.String, db.ForeignKey('ORDER.ORDER_NR'))
    PRODUCT_ID = db.Column(db.Integer, db.ForeignKey('PRODUCT.PRODUCT_ID'))

    # aantal van dit product in deze order
    Quantity = db.Column(db.Integer)
    Price_paid = db.Column(db.Float)


    def __repr__(self):
        return (
            f"<ORDER_LINE {self.ORDER_LINE_NR} order={self.ORDER_NR} "
            f"product={self.PRODUCT_ID}>"
        )