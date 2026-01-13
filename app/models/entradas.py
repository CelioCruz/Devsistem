from datetime import datetime
from decimal import Decimal
from ..extensions import db

class Entrada(db.Model):
    __tablename__ = 'entradas'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    descricao = db.Column(db.String(200))
    nf_chave = db.Column(db.String(44))
    nf_numero = db.Column(db.String(50))
    serie = db.Column(db.String(10))
    data_emissao = db.Column(db.Date)
    data_recebimento = db.Column(db.Date)
    nota_fiscal = db.Column(db.String(20))
    tipo_nota = db.Column(db.String(20))
    natureza_operacao = db.Column(db.String(20))
    fornecedor_id = db.Column(db.String(14), db.ForeignKey('tb_fornecedor.forn_cnpj'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('tb_us.us_reg'), nullable=False)
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento reverso
    itens = db.relationship('ItemEntrada', backref='entrada', lazy=True, cascade='all, delete-orphan')

class ItemEntrada(db.Model):
    __tablename__ = 'itens_entrada'

    id = db.Column(db.Integer, primary_key=True)
    entrada_id = db.Column(db.Integer, db.ForeignKey('entradas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('tb_produto.prod_reg'), nullable=True)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=True)

    produto = db.relationship('Produto', backref='itens_entrada')