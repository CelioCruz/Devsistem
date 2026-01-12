from ..extensions import db
from datetime import datetime


class LenteGenerica(db.Model):
    __tablename__ = 'tb_lente_generica'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo_base = db.Column(db.String(7), unique=True, nullable=False)
    descricao = db.Column(db.String(100), nullable=False)
    tipo_lente = db.Column(db.String(2), nullable=False)
    id_refracao = db.Column(db.String(10), nullable=False)
    preco_base = db.Column(db.Numeric(10, 2), default=0.00)
    antirreflexo = db.Column(db.String(50))
    escurecimento = db.Column(db.String(50))
    fabricante_id = db.Column(db.String(18), db.ForeignKey('tb_fornecedor.forn_cnpj'), nullable=True)
    
    # Faixas de dioptrias
    esf_min = db.Column(db.Numeric(4, 2), nullable=False)
    esf_max = db.Column(db.Numeric(4, 2), nullable=False)
    esf_step = db.Column(db.Numeric(3, 2), default=0.25)

    cil_min = db.Column(db.Numeric(4, 2), default=0.00)
    cil_max = db.Column(db.Numeric(4, 2), nullable=False)
    cil_step = db.Column(db.Numeric(3, 2), default=0.25)

    add_min = db.Column(db.Numeric(3, 2), nullable=False)
    add_max = db.Column(db.Numeric(3, 2), nullable=False)
    add_step = db.Column(db.Numeric(3, 2), default=0.25)

    altura_fixa = db.Column(db.String(2))

    # Relacionamento
    fabricante = db.relationship('Fornecedor', foreign_keys=[fabricante_id])


class Produto(db.Model):
    __tablename__ = 'tb_produto'

    # Chave primária
    prod_reg = db.Column(db.Integer, primary_key=True)    

    # Código de barras único (7 dígitos)
    prod_codigo_barras = db.Column(db.String(7), unique=True, nullable=False)

    # Campos comuns
    prod_nome = db.Column(db.String(150), nullable=False)
    prod_empresa = db.Column(db.String(100), nullable=False)
    prod_empresa_id = db.Column(db.Integer, db.ForeignKey('tb_empresa.emp_reg'), nullable=True)
    prod_preco_custo = db.Column(db.Numeric(10, 2), default=0.00)
    prod_tipo = db.Column(db.String(20), nullable=False)  # 'armacao' ou 'servico'

    # === Campo OBRIGATÓRIO para relacionamento com Fornecedor ===
    prod_fabricante_id = db.Column(db.String(18), db.ForeignKey('tb_fornecedor.forn_cnpj'), nullable=True)

    # === Campos específicos para ARMAÇÃO ===
    prod_tipo_aramacao = db.Column(db.String(2))        # 'AR' ou 'OC'
    prod_descricao_iniciais = db.Column(db.String(10))  # ex: 'PCAR'
    prod_peca = db.Column(db.String(20))                # ex: 'PC6225'
    prod_cor = db.Column(db.String(10))                 # ex: '003'
    prod_tamanho = db.Column(db.String(5))              # ex: '52'
    prod_ponte = db.Column(db.String(5))                # ex: '19'
    prod_codigo_arma = db.Column(db.String(20))         # ex: KP4510, PC6225

    # === Campos para SERVIÇO ===
    prod_descricao_servico = db.Column(db.Text)

    # Controle
    prod_ativo = db.Column(db.Boolean, default=True)
    prod_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # === RELACIONAMENTOS (sempre após todos os campos) ===
    empresa = db.relationship('Empresa', back_populates='produtos')
    fabricante = db.relationship('Fornecedor', foreign_keys=[prod_fabricante_id])