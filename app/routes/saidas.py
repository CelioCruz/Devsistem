from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import OrdemCompra
from ..models import SaidaNF, Devolucao, Cliente, Produto, Fornecedor

bp = Blueprint('saidas', __name__, url_prefix='/saidas')

#Rotas--

@bp.route('/')
def index():
    """Página inicial do módulo Saídas (menu de opções)"""
    return render_template('saidas/index.html')

@bp.route('/pedido-venda')
@login_required
def listar_pedidos_venda():
    # Assume que Ordens de Compra com status 'aprovada' viram pedidos de venda
    # OU crie um modelo PedidoVenda separado
    pedidos = OrdemCompra.query.filter_by(oc_status='aprovada').all()
    return render_template('saidas/lista_pedidos.html', pedidos=pedidos)

@bp.route('/pedido-venda/editar/<int:pedido_id>')
@login_required
def editar_pedido_venda(pedido_id):
    pedido = OrdemCompra.query.get_or_404(pedido_id)
    return render_template('saidas/form_pedido_venda.html', pedido=pedido)

@bp.route('/pedido-venda/finalizar/<int:pedido_id>', methods=['POST'])
@login_required
def finalizar_pedido_venda(pedido_id):
    pedido = OrdemCompra.query.get_or_404(pedido_id)
    if pedido.oc_status != 'aprovada':
        flash('Pedido não pode ser finalizado.', 'danger')
        return redirect(url_for('saidas.editar_pedido_venda', pedido_id=pedido_id))
    
    # Lógica de finalização:
    # - Gera Nota Fiscal de Saída
    # - Atualiza estoque
    # - Cria lançamento financeiro
    pedido.oc_status = 'finalizada'
    db.session.commit()
    flash(f'Pedido {pedido.oc_numero} finalizado com sucesso!', 'success')
    return redirect(url_for('saidas.listar_pedidos_venda'))

@bp.route('/nf-saida')
@login_required
def listar_nf_saida():
    nfes = SaidaNF.query.order_by(SaidaNF.snf_data_emissao.desc()).all()
    return render_template('saidas/lista_nf_saida.html', nfes=nfes)

@bp.route('/nf-saida/nova')
@login_required
def nova_nf_saida():
    return render_template('saidas/form_nf_saida.html')

@bp.route('/devolucoes')
@login_required
def listar_devolucoes():
    devolucoes = Devolucao.query.order_by(Devolucao.data_devolucao.desc()).all()
    return render_template('saidas/lista_devolucoes.html', devolucoes=devolucoes)

@bp.route('/devolucoes/nova')
@login_required
def nova_devolucao():
    return render_template('saidas/form_devolucao.html')

@bp.route('/pesquisa/<tipo>')
@login_required
def pesquisa(tipo):
    if tipo == 'cliente':
        q = request.args.get('q', '').strip()
        filtro = request.args.get('filtro', 'nome')

        query = Cliente.query
        if q:
            if filtro == 'codigo':
                query = query.filter(db.cast(Cliente.cli_reg, db.String).like(f"{q}%"))
            elif filtro == 'cpf':
                query = query.filter(Cliente.cli_cpf_cnpj.ilike(f"%{q}%"))
            else:
                query = query.filter(Cliente.cli_nome.ilike(f"%{q}%"))
        clientes = query.all()
        return render_template('admin/clientes.html', clientes=clientes, origem='saidas')

    elif tipo == 'produto':
        q = request.args.get('q', '').strip()
        filtro = request.args.get('filtro', 'descricao')

        query = Produto.query
        if q:
            if filtro == 'codigo':
                query = query.filter(Produto.prod_codigo_barras.like(f"{q}%"))
            elif filtro == 'ncm':
                query = query.filter(Produto.prod_ncm.ilike(f"%{q}%"))
            else:  # descricao
                query = query.filter(Produto.prod_nome.ilike(f"%{q}%"))
        produtos = query.all()
        # 👇 CORREÇÃO AQUI: usar o template de PESQUISA, não o de cadastro
        return render_template('admin/pesquisa_produto.html', produtos=produtos, origem='saidas')
    
    elif tipo == 'fornecedor':
        q = request.args.get('q', '').strip()
        filtro = request.args.get('filtro', 'razao')

        query = Fornecedor.query
        if q:
            if filtro == 'cnpj':
                query = query.filter(Fornecedor.forn_cnpj.like(f"%{q.replace('.', '').replace('/', '').replace('-', '')}%"))
            elif filtro == 'fantasia':
                query = query.filter(Fornecedor.forn_fantasia.ilike(f"%{q}%"))
            else:  # razao
                query = query.filter(Fornecedor.forn_razao.ilike(f"%{q}%"))

        fornecedores = query.all()
        return render_template('admin/pesquisa_fornecedor.html', fornecedores=fornecedores, origem='saidas')

    flash('Tipo de pesquisa inválido.', 'danger')
    return redirect(url_for('saidas.index'))

@bp.route('/devolucao')
@login_required
def lista_devolucoes():
    devolucoes = Devolucao.query.order_by(Devolucao.data_devolucao.desc()).all()
    return render_template('saidas/devolucoes.html', devolucoes=devolucoes)