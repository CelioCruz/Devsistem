from . import db
from datetime import datetime

class NotaFiscal(db.Model):
    __tablename__ = 'nota_fiscal'
    
    id = db.Column(db.Integer, primary_key=True)
    cv_numero = db.Column(db.Integer, nullable=False)
    cliente_id = db.Column(db.Integer)
    numero_nfe = db.Column(db.String(50))
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='emitida')  # emitida, cancelada, devolvida
    usuario_emissao = db.Column(db.Integer)