from ..extensions import db
from datetime import datetime

class CondicaoPagamento(db.Model):
    __tablename__ = 'tb_condicao_pagamento'

    cpg_reg = db.Column(db.Integer, primary_key=True)
    cpg_descricao = db.Column(db.String(100), nullable=False)  # ex: 'À vista', '30/60/90'
    cpg_dias = db.Column(db.Integer, nullable=True)  # dias padrão para vencimento (se aplicável)
    cpg_parcelas = db.Column(db.Integer, default=1)  # número de parcelas
    cpg_ativo = db.Column(db.Boolean, default=True)
    cpg_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    cpg_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    empresa = db.relationship('Empresa', back_populates='condicoes_pagamento')