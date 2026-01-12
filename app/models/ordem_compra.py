from ..extensions import db 

class OrdemCompra(db.Model):
    __tablename__ = 'ordem_compra'
    oc_reg = db.Column(db.Integer, primary_key=True)
    oc_numero = db.Column(db.String(20), unique=True)  # Número da OC
    oc_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'))
    oc_fornecedor_id = db.Column(db.String(14), db.ForeignKey('tb_fornecedor.forn_cnpj'))
    oc_numero_fornecedor = db.Column(db.String(50))
    oc_data_emissao = db.Column(db.Date, default=db.func.current_date())
    oc_data_previsao = db.Column(db.Date)
    oc_status = db.Column(db.String(20), default='rascunho')
    oc_condicao_pagamento = db.Column(db.String(50))
    oc_valor_frete = db.Column(db.Float, default=0.0)
    oc_empresa_responsavel_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'))
    oc_transportadora = db.Column(db.String(100))
    oc_entrega = db.Column(db.String(200))
    oc_transporte = db.Column(db.String(50))
    oc_etiquetagem = db.Column(db.String(100))
    oc_observacoes = db.Column(db.Text)
    oc_status = db.Column(db.String(20), default='rascunho')  # rascunho, aprovada, cancelada
    oc_usuario_criacao_id = db.Column(db.Integer, db.ForeignKey('tb_us.us_reg'))
    
    empresa = db.relationship('Empresa', foreign_keys=[oc_empresa_id])
    fornecedor = db.relationship('Fornecedor')
    empresa_responsavel = db.relationship('Empresa', foreign_keys=[oc_empresa_responsavel_id])
    usuario_criacao = db.relationship('Usuario')
    itens = db.relationship('ItemOrdemCompra', back_populates='ordem', cascade='all, delete-orphan')
    itens = db.relationship('ItemOrdemCompra', backref='ordem', lazy=True)


class ItemOrdemCompra(db.Model):
    __tablename__ = 'tb_item_ordem_compra'
    ioc_reg = db.Column(db.Integer, primary_key=True)
    ioc_ordem_compra_id = db.Column(db.Integer, db.ForeignKey('ordem_compra.oc_reg'))
    ioc_produto_id = db.Column(db.Integer, db.ForeignKey('tb_produto.prod_reg'), nullable=True)
    ioc_codigo_barras = db.Column(db.String(50))  # Para itens genéricos
    ioc_descricao = db.Column(db.String(200))
    ioc_quantidade = db.Column(db.Float)
    ioc_unidade = db.Column(db.String(10))
    ioc_valor_unitario = db.Column(db.Float)
    ioc_peso = db.Column(db.Float)
    ioc_total = db.Column(db.Float)    
    
    produto = db.relationship('Produto')