from ..extensions import db
from datetime import datetime

class Fornecedor(db.Model):
    __tablename__ = 'tb_fornecedor'

    forn_cnpj = db.Column(db.String(14), primary_key=True)
    forn_razao = db.Column(db.String(150), nullable=False)
    forn_fantasia = db.Column(db.String(100), nullable=True)
    forn_representante = db.Column(db.String(150), nullable=True)
    forn_tel_representante = db.Column(db.String(15), nullable=True)
    forn_cep = db.Column(db.String(9), nullable=True)
    forn_endereco = db.Column(db.String(200), nullable=True)
    forn_bairro = db.Column(db.String(100), nullable=True)
    forn_cidade = db.Column(db.String(100), nullable=True)
    forn_uf = db.Column(db.String(2), nullable=True)
    forn_telefone = db.Column(db.String(15), nullable=True)
    forn_email = db.Column(db.String(100), nullable=True)
    forn_ativo = db.Column(db.Boolean, default=True)
    forn_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Chave estrangeira para empresa
    forn_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)

    # Relacionamento com Empresa
    empresa = db.relationship('Empresa', back_populates='fornecedores')