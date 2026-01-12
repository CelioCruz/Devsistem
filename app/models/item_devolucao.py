from . import db
from datetime import datetime

class ItemDevolucao(db.Model):
    __tablename__ = 'item_devolucao'
    
    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(db.Integer, db.ForeignKey('devolucao.id'))
    item_venda_id = db.Column(db.Integer)
    tipo_item = db.Column(db.String(20))  # 'armação', 'lente', etc.
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10, 2))