from ..extensions import db

# --- TABELA INTERMEDIÁRIA: Empresa x Ambientes ---
empresa_tem_ambiente = db.Table('tb_empresa_tem_ambiente',
    db.Column('emp_reg', db.Integer, db.ForeignKey('tb_empresa.emp_reg'), primary_key=True),
    db.Column('amb_id', db.Integer, db.ForeignKey('tb_ambiente.amb_id'), primary_key=True)
)

# Agora importa todos os modelos
from .ambiente import Ambiente
from .usuario import Usuario
from .empresa import Empresa
from .fornecedor import Fornecedor
from .cliente import Cliente
from .vendedor import Vendedor
from .produto import Produto, LenteGenerica
from .entradas import Entrada, ItemEntrada
from .banco import Banco
from .tipo_cartao import TipoCartao
from .tipo_carne import TipoCarne
from .condi_pagamento import CondicaoPagamento
from .operacao_conciliacao import OperacaoConciliacao
from .feriado import Feriado
from .custo_contabil import CentroCusto
from .natureza_operacao import NaturezaOperacao
from .ordem_compra import OrdemCompra, ItemOrdemCompra
from .devolucao import Devolucao
from .saida_nf import SaidaNF
from .ordem_servico import OrdemServico
from .caixa import Caixa
from .item_devolucao import ItemDevolucao
from .convenio import Convenio
from .laboratorio import Laboratorio
from .medico import Medico

# Exportar db e login_manager se necessário
from ..extensions import login_manager