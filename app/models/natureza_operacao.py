from ..extensions import db
from datetime import datetime

class NaturezaOperacao(db.Model):
    __tablename__ = 'tb_natureza_operacao'
    no_id = db.Column(db.Integer, primary_key=True)
    no_codigo = db.Column(db.String(10), unique=True, nullable=False)
    no_descricao = db.Column(db.String(200), nullable=False)