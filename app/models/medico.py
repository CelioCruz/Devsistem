from ..extensions import db
from datetime import datetime

class Medico(db.Model):
    __tablename__ = 'medico'
    med_id = db.Column(db.Integer, primary_key=True)
    med_nome = db.Column(db.String(100), nullable=False)
    med_crm = db.Column(db.String(20))
    med_ativo = db.Column(db.Boolean, default=True)