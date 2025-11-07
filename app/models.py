from . import db

class WEBUSER(db.Model):
    __tablename__ = 'WEBUSER'  # moet exact overeenkomen met de tabelnaam in Supabase (kleine letters aanbevolen)
    
    WEBUSER_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<WEBUSER {self.Name}>'

from . import db

class CLIENT(db.Model):
    __tablename__ = 'CLIENT'

    CLIENT_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), nullable=False)
    Country = db.Column(db.String(100))
    Postcode = db.Column(db.String(20))
    city = db.Column(db.String(100))
    street = db.Column(db.String(100))
    housenr = db.Column(db.String(20))
    BTW_VAT = db.Column("BTW/VAT", db.String(50))  # ← let op: underscore in plaats van "/"

    def __repr__(self):
        return f'<CLIENT {self.Name}>'