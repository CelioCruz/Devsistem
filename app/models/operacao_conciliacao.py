from ..extensions import db
from datetime import datetime

class OperacaoConciliacao(db.Model):
    __tablename__ = 'tb_operacao_conciliacao'

    opc_reg = db.Column(db.Integer, primary_key=True)
    opc_descricao = db.Column(db.String(100), nullable=False)  # ex: 'Depósito', 'Saque', 'Transferência'
    opc_tipo = db.Column(db.String(10), nullable=False)  # 'entrada', 'saida', 'ajuste'
    opc_ativo = db.Column(db.Boolean, default=True)
    opc_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Chave estrangeira para empresa (opcional)
    opc_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)

    # Relacionamento com Empresa (usa string para evitar importação circular)
    empresa = db.relationship('Empresa', back_populates='operacoes_conciliacao')