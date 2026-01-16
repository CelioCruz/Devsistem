from ..extensions import db
from datetime import datetime
from . import empresa_tem_ambiente  # tabela intermediária


class Empresa(db.Model):
    __tablename__ = 'tb_empresa'

    emp_reg = db.Column(db.Integer, primary_key=True)
    emp_razao_social = db.Column(db.String(150), nullable=False)
    emp_nome_fantasia = db.Column(db.String(100), nullable=False)
    emp_cnpj = db.Column(db.String(14), unique=True, nullable=False)
    emp_ie = db.Column(db.String(20), nullable=True)
    emp_im = db.Column(db.String(20), nullable=True)
    emp_cep = db.Column(db.String(9), nullable=True)
    emp_endereco = db.Column(db.String(200), nullable=True)
    emp_bairro = db.Column(db.String(100), nullable=True)
    emp_cidade = db.Column(db.String(100), nullable=True)
    emp_uf = db.Column(db.String(2), nullable=True)
    emp_telefone = db.Column(db.String(15), nullable=True)
    emp_email = db.Column(db.String(100), nullable=True)

    # 🔐 Certificado Digital
    emp_certificado_a1 = db.Column(db.LargeBinary, nullable=True)  # arquivo .pfx/.p12 em binário
    emp_senha_certificado = db.Column(db.String(200), nullable=True)  # ⚠️ ideal: criptografar antes de salvar

    # 📄 Configuração NF-e/NFC-e
    emp_config_nfce = db.Column(db.Text, nullable=True)

    # 🏢 Tipo Tributário (MEI, Simples, Lucro Real, etc.)
    emp_tipo = db.Column(db.String(50), nullable=True)  # ex: "Simples Nacional"

    # ⏳ Controle de Licença / Temporizador
    emp_licenca_tipo = db.Column(db.String(20), nullable=False, default='permanente')  # 'permanente' ou 'temporaria'
    emp_licenca_data_fim = db.Column(db.Date, nullable=True)  # data de expiração (se temporária)
    emp_licenca_desativar_tempo = db.Column(db.Boolean, nullable=False, default=False)  # se True → ignora limite

    # 🟢 Status
    emp_ativo = db.Column(db.Boolean, default=True)
    emp_datcad = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relacionamentos 1:N
    usuarios = db.relationship('Usuario', back_populates='empresa', lazy=True)
    clientes = db.relationship('Cliente', back_populates='empresa', lazy=True)
    fornecedores = db.relationship('Fornecedor', back_populates='empresa', lazy=True)
    produtos = db.relationship('Produto', back_populates='empresa', lazy=True)

    # Relacionamentos contábeis/administrativos
    bancos = db.relationship('Banco', back_populates='empresa', lazy='dynamic')
    tipos_cartao = db.relationship('TipoCartao', back_populates='empresa', lazy='dynamic')
    tipos_carne = db.relationship('TipoCarne', back_populates='empresa', lazy='dynamic')
    condicoes_pagamento = db.relationship('CondicaoPagamento', back_populates='empresa', lazy='dynamic')
    operacoes_conciliacao = db.relationship('OperacaoConciliacao', back_populates='empresa', lazy='dynamic')
    feriados = db.relationship('Feriado', back_populates='empresa', lazy='dynamic')
    centros_custo = db.relationship('CentroCusto', back_populates='empresa', lazy='dynamic')

    # Relacionamento M:N com Ambientes
    ambientes_permitidos = db.relationship(
        'Ambiente',
        secondary=empresa_tem_ambiente,
        lazy='subquery',
        back_populates='empresas'
    )