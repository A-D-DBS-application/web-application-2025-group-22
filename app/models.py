from . import db

class WEBUSER(db.Model):
    __tablename__ = 'WEBUSER'  # moet exact overeenkomen met de tabelnaam in Supabase (kleine letters aanbevolen)
    
    WEBUSER_ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<WEBUSER {self.Name}>'
