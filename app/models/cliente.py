from ..extensions import db
from datetime import datetime

class Cliente(db.Model):
    __tablename__ = 'tb_cliente'

    cli_reg = db.Column(db.Integer, primary_key=True)
    cli_nome = db.Column(db.String(150), nullable=False)
    cli_nasc = db.Column(db.Date, nullable=True)
    cli_cpf_cnpj = db.Column(db.String(18), unique=True, nullable=True)
    cli_cep = db.Column(db.String(9), nullable=True)
    cli_endereco = db.Column(db.String(200), nullable=True)
    cli_bairro = db.Column(db.String(100), nullable=True)
    cli_cidade = db.Column(db.String(100), nullable=True)
    cli_uf = db.Column(db.String(2), nullable=True)
    cli_pai = db.Column(db.String(150), nullable=True)
    cli_mae = db.Column(db.String(150), nullable=True)
    cli_telefone = db.Column(db.String(15), nullable=True)
    cli_ativo = db.Column(db.Boolean, default=True)
    cli_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Chave estrangeira para empresa
    cli_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)

    # Relacionamento com Empresa
    empresa = db.relationship('Empresa', back_populates='clientes')