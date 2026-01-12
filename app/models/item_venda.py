from ..extensions import db
from datetime import datetime

class ItemVenda(db.Model):
    __tablename__ = 'item_venda'
    
    id = db.Column(db.Integer, primary_key=True)
    cv_numero = db.Column(db.Integer, nullable=False)
    produto_id = db.Column(db.Integer)
    tipo = db.Column(db.String(20))  # 'armação', 'lente_direita', 'lente_esquerda'
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='vendido')  # vendido, devolvido, cancelado
    devolvido_em = db.Column(db.DateTime)