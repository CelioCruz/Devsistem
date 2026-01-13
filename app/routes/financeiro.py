# app/routes/financeiro.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from datetime import datetime, date, timedelta
from ..models import Cliente, Fornecedor, SaidaNF, Entrada, Caixa

bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

@bp.route('/')
@login_required
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    contas_hoje = []  # Lista vazia por enquanto (modelos ainda não criados)
    return render_template('financeiro/index.html', contas_hoje=contas_hoje, today=today)

@bp.route('/conciliacao')
@login_required
def conciliacao():
    flash('Módulo em desenvolvimento.', 'info')
    return redirect(url_for('financeiro.index'))

@bp.route('/plano-contas')
@login_required
def plano_contas():
    tipo = request.args.get('tipo', 'tanto_faz')
    contas = []  # temporário (será implementado depois)
    return render_template('financeiro/plano_contas.html', tipo=tipo, contas=contas)

@bp.route('/caixas')
@login_required
def caixas():
    """Relatório de caixas: abertura e fechamento por dia"""
    # Busca todos os caixas, ordenados por data (desc)
    caixas = Caixa.query.order_by(Caixa.cai_data.desc()).all()
    return render_template('financeiro/caixas.html', caixas=caixas)

@bp.route('/historico/cliente')
@login_required
def historico_cliente():
    """Etapa 1: exibe tela de pesquisa de cliente"""
    return render_template('admin/pesquisa_cliente_historico.html', origem='financeiro_historico_cliente')

@bp.route('/historico/cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def historico_cliente_detalhes(cliente_id):
    """Etapa 2: exibe vendas do cliente em um período"""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    if request.method == 'POST':
        data_ini = request.form.get('data_ini')
        data_fim = request.form.get('data_fim')
    else:
        # Padrão: último mês
        hoje = date.today()
        data_ini = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        data_fim = hoje.strftime('%Y-%m-%d')

    # Busca vendas (Saídas) do cliente no período
    # Nota: snf_cliente_id é String (CPF/CNPJ), então precisa converter cliente_id para CPF/CNPJ
    cliente_cpf_cnpj = cliente.cli_cpf_cnpj
    vendas = SaidaNF.query.filter(
        SaidaNF.snf_cliente_id == cliente_cpf_cnpj,
        SaidaNF.snf_data_emissao >= data_ini,
        SaidaNF.snf_data_emissao <= data_fim
    ).order_by(SaidaNF.snf_data_emissao.desc()).all()

    return render_template(
        'financeiro/historico_cliente_detalhes.html',
        cliente=cliente,
        vendas=vendas,
        data_ini=data_ini,
        data_fim=data_fim
    )

@bp.route('/historico/fornecedor')
@login_required
def historico_fornecedor():
    """Etapa 1: exibe tela de pesquisa de fornecedor"""
    return render_template('admin/pesquisa_fornecedor_historico.html', origem='financeiro_historico_fornecedor')

@bp.route('/historico/fornecedor/<int:fornecedor_id>', methods=['GET', 'POST'])
@login_required
def historico_fornecedor_detalhes(fornecedor_id):
    """Etapa 2: exibe entradas do fornecedor em um período"""
    fornecedor = Fornecedor.query.get_or_404(fornecedor_id)
    
    if request.method == 'POST':
        data_ini = request.form.get('data_ini')
        data_fim = request.form.get('data_fim')
    else:
        hoje = date.today()
        data_ini = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        data_fim = hoje.strftime('%Y-%m-%d')

    # Busca entradas (notas fiscais de entrada) no período
    # Nota: fornecedor_id é String (CNPJ)
    fornecedor_cnpj = fornecedor.forn_cnpj
    entradas = Entrada.query.filter(
        Entrada.fornecedor_id == fornecedor_cnpj,
        Entrada.data_emissao >= data_ini,
        Entrada.data_emissao <= data_fim
    ).order_by(Entrada.data_emissao.desc()).all()

    return render_template(
        'financeiro/historico_fornecedor_detalhes.html',
        fornecedor=fornecedor,
        entradas=entradas,
        data_ini=data_ini,
        data_fim=data_fim
    )