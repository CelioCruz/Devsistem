from . import db
from datetime import datetime

class Devolucao(db.Model):
    __tablename__ = 'devolucao'
    
    id = db.Column(db.Integer, primary_key=True)
    cv_numero = db.Column(db.Integer, nullable=False)
    cliente_id = db.Column(db.Integer)
    tipo = db.Column(db.String(20))  # 'parcial', 'total'
    valor_credito = db.Column(db.Numeric(10, 2))
    observacao = db.Column(db.Text)
    data_devolucao = db.Column(db.DateTime, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer)  # quem fez a devolução
    
    # Relacionamento com itens (opcional)
    itens = db.relationship('ItemDevolucao', backref='devolucao', lazy=True)