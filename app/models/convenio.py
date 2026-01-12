from ..extensions import db
from datetime import datetime

class Convenio(db.Model):
    __tablename__ = 'convenio'
    conv_id = db.Column(db.Integer, primary_key=True)
    conv_nome = db.Column(db.String(100), nullable=False)
    conv_ativo = db.Column(db.Boolean, default=True)