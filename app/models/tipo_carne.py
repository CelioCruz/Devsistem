from ..extensions import db
from datetime import datetime

class TipoCarne(db.Model):
    __tablename__ = 'tb_tipo_carne'

    tcn_reg = db.Column(db.Integer, primary_key=True)
    tcn_descricao = db.Column(db.String(100), nullable=False)  # ex: 'Parcelado sem juros', 'Com juros mensais'
    tcn_ativo = db.Column(db.Boolean, default=True)
    tcn_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    tcn_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='tipos_carne')