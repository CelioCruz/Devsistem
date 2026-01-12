from ..extensions import db
from datetime import datetime

class Laboratorio(db.Model):
    __tablename__ = 'laboratorio'
    lab_id = db.Column(db.Integer, primary_key=True)
    lab_nome = db.Column(db.String(100), nullable=False)
    lab_contato = db.Column(db.String(100))
    lab_ativo = db.Column(db.Boolean, default=True)