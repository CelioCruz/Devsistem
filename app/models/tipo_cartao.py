from ..extensions import db
from datetime import datetime

class TipoCartao(db.Model):
    __tablename__ = 'tb_tipo_cartao'
    
    tca_reg = db.Column(db.Integer, primary_key=True)
    tca_descricao = db.Column(db.String(100), nullable=False)
    tca_tipo = db.Column(db.String(10), nullable=False)  # 'credito' ou 'debito'
    tca_taxa_credito = db.Column(db.Numeric(5, 2), default=0.00)  # ex: 3.50
    tca_taxa_debito = db.Column(db.Numeric(5, 2), default=0.00)  # ex: 2.00
    tca_parcelas = db.Column(db.Integer, nullable=False, default=1)  # 1 a 12
    tca_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    tca_ativo = db.Column(db.Boolean, default=True)
    empresa = db.relationship('Empresa', back_populates='tipos_cartao')