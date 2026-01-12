from ..extensions import db
from datetime import datetime

class Banco(db.Model):
    __tablename__ = 'tb_banco'

    ban_reg = db.Column(db.Integer, primary_key=True)
    ban_codigo = db.Column(db.String(5), nullable=False, unique=True)
    ban_nome = db.Column(db.String(100), nullable=False)
    ban_ativo = db.Column(db.Boolean, default=True)
    ban_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    ban_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='bancos')