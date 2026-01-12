from ..extensions import db
from datetime import datetime

class CentroCusto(db.Model):
    __tablename__ = 'tb_centro_custo'

    cct_reg = db.Column(db.Integer, primary_key=True)
    cct_codigo = db.Column(db.String(20), nullable=False, unique=True)  # ex: 'CC-001'
    cct_descricao = db.Column(db.String(150), nullable=False)
    cct_ativo = db.Column(db.Boolean, default=True)
    cct_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    cct_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='centros_custo')