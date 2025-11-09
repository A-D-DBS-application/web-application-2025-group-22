from . import db

class WEBUSER(db.Model):
    __tablename__ = 'WEBUSER'

    WEBUSER_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), unique=True, nullable=False)
    Email = db.Column(db.String(150))
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'), nullable=False)

    supplier = db.relationship('SUPPLIER', backref='webusers')

    def __repr__(self):
        return f'<WEBUSER {self.Name}>'


class CLIENT(db.Model):
    __tablename__ = 'CLIENT'

    CLIENT_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Country = db.Column(db.String(100))
    Postcode = db.Column(db.String(20))
    city = db.Column(db.String(100))
    street = db.Column(db.String(100))
    housenr = db.Column(db.String(20))
    BTW_VAT = db.Column("BTW/VAT", db.String(50))

    orders = db.relationship('ORDER', backref='client', lazy=True)

    def __repr__(self):
        return f'<CLIENT {self.Name}>'


class SUPPLIER(db.Model):
    __tablename__ = 'SUPPLIER'

    SUPPLIER_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    Postal_code = db.Column("postal code", db.String(20))
    city = db.Column(db.String(100))
    street = db.Column(db.String(100))
    housenumber = db.Column(db.String(20))
    VAT_BTW = db.Column("VAT/BTW", db.String(50))
    Phone_nr = db.Column("phone nr", db.String(50))

    products = db.relationship('PRODUCT', backref='supplier', lazy=True)
    orders = db.relationship('ORDER', backref='supplier', lazy=True)

    def __repr__(self):
        return f'<SUPPLIER {self.name}>'


class PRODUCT(db.Model):
    __tablename__ = 'PRODUCT'

    PRODUCT_NR = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), nullable=False)
    Unit_volume = db.Column("Unit volume", db.Text, nullable=False)  # safe Float
    Unit_cost = db.Column("Unit cost", db.Integer, nullable=False)       # safe Float
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'), nullable=False)

    orders = db.relationship('ORDER', backref='product', lazy=True)

    def __repr__(self):
        return f'<PRODUCT {self.Name} (NR={self.PRODUCT_NR})>'


class COST(db.Model):
    __tablename__ = 'COST'

    FACTUUR_NR = db.Column(db.Integer, primary_key=True, autoincrement=True)
    aantal_stuks = db.Column("aantal stuks", db.Integer, nullable=False)
    Transport_price_per_unit = db.Column("Transport price per unit", db.Float, nullable=False)
    Total_transport_cost = db.Column("Total transport cost", db.Float, nullable=False)
    Stockage_price_per_unit = db.Column("Stockage price per unit", db.Float, nullable=False)
    Total_stockage_cost = db.Column("Total stockage cost", db.Float, nullable=False)
    Total_cost = db.Column("Total cost", db.Float, nullable=False)

    orders = db.relationship('ORDER', backref='cost', lazy=True)

    def __repr__(self):
        return f'<COST FACTUUR_NR={self.FACTUUR_NR}>'


class ORDER(db.Model):
    __tablename__ = 'ORDER'

    ORDER_NR = db.Column(db.Integer, primary_key=True, autoincrement=True)
    FACTUUR_NR = db.Column(db.Integer, db.ForeignKey('COST.FACTUUR_NR'), nullable=False)
    CLIENT_ID = db.Column(db.Integer, db.ForeignKey('CLIENT.CLIENT_ID'), nullable=False)
    SUPPLIER_ID = db.Column(db.Integer, db.ForeignKey('SUPPLIER.SUPPLIER_ID'), nullable=False)
    PRODUCT_NR = db.Column(db.Integer, db.ForeignKey('PRODUCT.PRODUCT_NR'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_sell_price = db.Column("total sell price", db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f'<ORDER ORDER_NR={self.ORDER_NR} FACTUUR_NR={self.FACTUUR_NR}>'
