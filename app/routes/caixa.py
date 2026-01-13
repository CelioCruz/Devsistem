from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import OrdemServico, Cliente, Caixa, Devolucao, ItemDevolucao, Usuario, Produto, Convenio, Laboratorio, Medico
from datetime import datetime, date, timedelta
from decimal import Decimal
from ..utils.gerar_proximo import gerar_proximo_cv, gerar_proximo_os 

bp = Blueprint('caixa', __name__, url_prefix='/caixa')

@bp.route('/')
@login_required
def index():
    hoje = date.today()
    
    # Busca o último caixa do dia (se existir)
    ultimo_caixa = Caixa.query.filter(
        Caixa.cai_data == hoje
    ).order_by(Caixa.cai_reg.desc()).first()

    # Determina o estado atual
    if not ultimo_caixa:
        estado = 'fechado'  # Nenhum caixa hoje → permite Novo Caixa
    elif ultimo_caixa.cai_status == 'aberto':
        estado = 'aberto'
    elif ultimo_caixa.cai_status == 'encerrado':
        estado = 'encerrado'
    elif ultimo_caixa.cai_status == 'finalizado_dia':
        estado = 'finalizado'
    else:
        estado = 'fechado'

    return render_template('caixa/index.html', estado_caixa=estado)

# --- Abertura de Caixa ---
@bp.route('/abrir', methods=['GET', 'POST'])
@login_required
def abrir_caixa():
    # Verifica se o dia já foi finalizado
    dia_finalizado = Caixa.query.filter(
        Caixa.cai_data == date.today(),
        Caixa.cai_status == 'finalizado_dia'
    ).first()
    
    if dia_finalizado:
        flash('O caixa do dia já foi finalizado. Aguarde o próximo dia útil.', 'danger')
        return redirect(url_for('caixa.index'))

    if Caixa.query.filter_by(cai_status='aberto').first():
        flash('Já existe um caixa aberto!', 'warning')
        return redirect(url_for('caixa.index'))

    if request.method == 'POST':
        saldo_inicial = Decimal(request.form.get('saldo_inicial', '0.00'))
        observacao = request.form.get('observacao', '').strip()
        
        novo_caixa = Caixa(
            cai_loja='01',
            cai_usuario_abertura=current_user.us_reg,
            cai_saldo_inicial=saldo_inicial,
            cai_observacao=observacao,  # ← salva a observação
            cai_status='aberto'
        )
        db.session.add(novo_caixa)
        db.session.commit()
        flash('Caixa aberto com sucesso!', 'success')
        return redirect(url_for('caixa.index'))
    
    return render_template('caixa/abertura_caixa.html')

# --- Fechamento de Caixa ---
@bp.route('/fechar', methods=['GET', 'POST'])
@login_required
def fechar_caixa():
    # Busca o caixa ABERTO de HOJE
    from datetime import date
    hoje = date.today()
    caixa = Caixa.query.filter_by(cai_data=hoje, cai_status='aberto').first_or_404()

    if request.method == 'POST':
        # Valores recebidos
        cai_dinheiro_caixa = Decimal(request.form.get('dinheiro_caixa', '0.00'))
        cai_dinheiro_retrada = Decimal(request.form.get('dinheiro_retrada', '0.00'))
        cai_cheque_caixa = Decimal(request.form.get('cheque_caixa', '0.00'))
        cai_cheque_retrada = Decimal(request.form.get('cheque_retrada', '0.00'))
        cai_pix_caixa = Decimal(request.form.get('pix_caixa', '0.00'))
        cai_cartao_caixa = Decimal(request.form.get('cartao_caixa', '0.00'))
        cai_ticket_caixa = Decimal(request.form.get('ticket_caixa', '0.00'))
        cai_convenio_caixa = Decimal(request.form.get('convenio_caixa', '0.00'))
        cai_banco_caixa = Decimal(request.form.get('banco_caixa', '0.00'))
        cai_carnet_caixa = Decimal(request.form.get('carnet_caixa', '0.00'))
        observacao = request.form.get('observacao', '').strip()

        # Cálculos
        total_recebido = (
            cai_dinheiro_caixa + cai_cheque_caixa + cai_pix_caixa +
            cai_cartao_caixa + cai_ticket_caixa + cai_convenio_caixa +
            cai_banco_caixa + cai_carnet_caixa
        )
        total_retirado = cai_dinheiro_retrada + cai_cheque_retrada
        saldo_final = (caixa.cai_saldo_inicial or Decimal('0.00')) + total_recebido - total_retirado

        # Total registrado pelo sistema (substitua pela sua lógica real)
        # Exemplo: soma de todas as vendas do dia
        total_sistema = Decimal("813.00")  # ← Substitua por lógica real depois

        falta = saldo_final - total_sistema
        malote = Decimal("0.00")

        # Atualiza o caixa
        caixa.cai_dinheiro_caixa = cai_dinheiro_caixa
        caixa.cai_dinheiro_retrada = cai_dinheiro_retrada
        caixa.cai_cheque_caixa = cai_cheque_caixa
        caixa.cai_cheque_retrada = cai_cheque_retrada
        caixa.cai_pix_caixa = cai_pix_caixa
        caixa.cai_cartao_caixa = cai_cartao_caixa
        caixa.cai_ticket_caixa = cai_ticket_caixa
        caixa.cai_convenio_caixa = cai_convenio_caixa
        caixa.cai_banco_caixa = cai_banco_caixa
        caixa.cai_carnet_caixa = cai_carnet_caixa
        caixa.cai_observacao = observacao
        caixa.cai_total_conferencia = saldo_final
        caixa.cai_total_sistema = total_sistema
        caixa.cai_falta = falta
        caixa.cai_malote = malote
        caixa.cai_hora_fechamento = datetime.utcnow()
        caixa.cai_usuario_fechamento = current_user.us_reg
        
        # 👇 STATUS CORRETO PARA SEU FLUXO 👇
        caixa.cai_status = 'encerrado'  # não 'fechado'

        db.session.commit()
        flash('Caixa fechado com sucesso!', 'success')
        return redirect(url_for('caixa.index'))

    # Para GET: renderiza o formulário
    return render_template('caixa/fechamento_caixa.html', caixa=caixa)

@bp.route('/reabrir-caixa', methods=['GET', 'POST'])
@login_required
def reabrir_caixa():
    saldo_inicial = request.args.get('saldo_inicial', 0, type=float)
    
    if request.method == 'POST':
        # Reabre o caixa existente (não cria novo!)
        hoje = date.today()
        caixa = Caixa.query.filter_by(cai_data=hoje, cai_status='encerrado').first()
        if caixa:
            caixa.cai_status = 'aberto'
            caixa.cai_saldo_inicial = float(request.form.get('saldo_inicial', 0))
            db.session.commit()
            flash('Caixa reaberto com sucesso!', 'success')
        else:
            flash('Nenhum caixa encerrado encontrado para reabrir.', 'warning')
        return redirect(url_for('caixa.index'))

    return render_template('caixa/reabrir_caixa.html', 
                      saldo_inicial=saldo_inicial,
                      hoje=date.today())

@bp.route('/resumo/imprimir')
@login_required
def imprimir_resumo():
    # Busca caixa aberto
    caixa = Caixa.query.filter_by(cai_status='aberto').first()
    
    # Se não encontrar aberto, busca o último caixa (sem depender de cai_hora_abertura)
    if not caixa:
        # Ordena por cai_reg (ID) decrescente como fallback
        caixa = Caixa.query.order_by(Caixa.cai_reg.desc()).first()
    
    if not caixa:
        flash('Nenhum caixa encontrado para gerar o resumo.', 'warning')
        return redirect(url_for('caixa.index'))
    
    return render_template('caixa/resumo_impressao.html', caixa=caixa)


@bp.route('/resumo/visualizar')
@login_required
def visualizar_resumo():
    caixa = Caixa.query.filter_by(cai_status='aberto').first()
    if not caixa:
        caixa = Caixa.query.order_by(Caixa.cai_reg.desc()).first()
    
    if not caixa:
        flash('Nenhum caixa encontrado para gerar o resumo.', 'warning')
        return redirect(url_for('caixa.index'))
    
    return render_template('caixa/resumo_visualizacao.html', caixa=caixa)

from datetime import date

@bp.route('/finalizar-dia', methods=['GET', 'POST'])
@login_required
def finalizar_dia():
    from datetime import date
    hoje = date.today()
    
    caixas_ativos = Caixa.query.filter(
        Caixa.cai_data == hoje,
        Caixa.cai_status.in_(['aberto', 'encerrado'])
    ).all()

    if not caixas_ativos:
        flash('Não existe caixa aberto ou pendente para finalização hoje.', 'warning')
        return redirect(url_for('caixa.index'))

    if request.method == 'POST':
        for c in caixas_ativos:
            # 👇 SÓ CAMPOS QUE EXISTEM NO SEU MODELO 👇
            total_recebido = (
                (c.cai_dinheiro_caixa or 0) +
                (c.cai_pix_caixa or 0) +
                (c.cai_cartao_caixa or 0)
            )
            total_retirado = (c.cai_dinheiro_retrada or 0) + (c.cai_cheque_retrada or 0)
            c.cai_saldo_final = (c.cai_saldo_inicial or 0) + total_recebido - total_retirado
            c.cai_hora_fechamento = datetime.utcnow()
            c.cai_status = 'finalizado_dia'
        
        db.session.commit()
        flash('Dia finalizado com sucesso!', 'success')
        return redirect(url_for('caixa.imprimir_resumo_dia'))
    
    return render_template('caixa/finalizar_dia_confirm.html')

@bp.route('/imprimir-resumo-dia')
@login_required
def imprimir_resumo_dia():
    """Imprime o resumo de todos os caixas do dia."""
    caixas = Caixa.query.filter(
        Caixa.cai_data == date.today(),
        Caixa.cai_status == 'finalizado_dia'
    ).all()
    
    if not caixas:
        flash('Nenhum caixa finalizado para imprimir.', 'warning')
        return redirect(url_for('caixa.index'))
    
    return render_template('caixa/resumo_dia_impressao.html', caixas=caixas, hoje=date.today())

# --- PDV (Venda Rápida) ---
@bp.route('/pdv', methods=['GET', 'POST'])
@login_required
def pdv():
    loja_id = getattr(current_user, 'loja_id', '01')
    if not loja_id:
        loja_id = '01'

    caixa_aberto = Caixa.query.filter_by(
        cai_loja=loja_id,
        cai_status='aberto'
    ).first()
    
    if not caixa_aberto:
        flash('Abra o caixa antes de realizar vendas.', 'warning')
        return redirect(url_for('caixa.index'))
    
    if request.method == 'POST':
        # Processar venda (simplificado)
        produto_id = request.form.get('produto_id')
        quantidade = int(request.form.get('quantidade', 1))
        # ... lógica de venda ...
        flash('Venda registrada com sucesso!', 'success')
        return redirect(url_for('caixa.pdv'))
    
    return render_template('caixa/pdv.html', caixa=caixa_aberto)

# --- Sangria / Suprimento ---
@bp.route('/movimentacao', methods=['GET', 'POST'])
@login_required
def movimentacao_caixa():
    caixa = Caixa.query.filter_by(
        cai_loja=current_user.loja_id,
        cai_status='aberto'
    ).first_or_404()
    
    if request.method == 'POST':
        tipo = request.form.get('tipo')  # 'sangria' ou 'suprimento'
        valor = Decimal(request.form.get('valor', '0.00'))
        observacao = request.form.get('observacao', '')
        if observacao:
            caixa.cai_observacao = observacao
        
        if tipo == 'sangria':
            # Registrar sangria (subtrai do saldo)
            pass
        elif tipo == 'suprimento':
            # Registrar suprimento (adiciona ao saldo)
            pass
        
        flash(f'{tipo.capitalize()} registrada com sucesso!', 'success')
        return redirect(url_for('caixa.movimentacao_caixa'))
    
    return render_template('caixa/sangria_suprimento.html', caixa=caixa)

# --- Criar nova OS (simulando finalização de venda) ---
@bp.route('/nova-venda', methods=['GET', 'POST'])
@login_required
def nova_venda():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        loja_id = request.form.get('loja_id', '01')  # padrão loja 01
        
        # Gera números
        novo_cv = gerar_proximo_cv()
        novo_os = gerar_proximo_os(loja_id)
        
        # Cria OS
        os = OrdemServico(
            os_numero=novo_os,
            cv_numero=novo_cv,
            loja_id=loja_id.zfill(2),
            cliente_id=cliente_id or None,
            status='venda_concluida'
        )
        db.session.add(os)
        db.session.commit()
        
        flash(f'Venda criada! CV: {novo_cv}, OS: {novo_os}', 'success')
        return redirect(url_for('caixa.monitor_producao'))
    
    clientes = Cliente.query.all()
    return render_template('caixa/nova_venda.html', clientes=clientes)

# --- Monitor de Produção ---
@bp.route('/producao')
@login_required
def monitor_producao():
    ordens = OrdemServico.query.filter(
        OrdemServico.status.in_(['venda_concluida', 'liberado_compra'])
    ).order_by(OrdemServico.data_emissao.desc()).all()
    return render_template('caixa/monitor_producao.html', ordens=ordens)

# --- Visualizar OS (somente leitura) ---
@bp.route('/producao/<os_numero>')
@login_required
def visualizar_os(os_numero):
    ordem = OrdemServico.query.get_or_404(os_numero)
    return render_template('caixa/visualizar_os.html', ordem=ordem)

# --- Ações: Translado e Cancelamento ---
@bp.route('/producao/<os_numero>/translado', methods=['POST'])
@login_required
def translado_loja_estoque(os_numero):
    ordem = OrdemServico.query.get_or_404(os_numero)
    if ordem.status == 'venda_concluida':
        ordem.status = 'liberado_compra'
        db.session.commit()
        flash('OS liberada para compra no estoque!', 'success')
    return redirect(url_for('caixa.monitor_producao'))

@bp.route('/producao/<os_numero>/cancelar', methods=['POST'])
@login_required
def cancelar_os(os_numero):
    ordem = OrdemServico.query.get_or_404(os_numero)
    ordem.status = 'cancelada'
    db.session.commit()
    flash('OS cancelada.', 'info')
    return redirect(url_for('caixa.monitor_producao'))

@bp.route('/os/<os_numero>/quebra-armação', methods=['GET', 'POST'])
@login_required
def registrar_quebra_armação(os_numero):
    """Registra devolução por quebra de armação na montagem"""
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    # Só permite se estiver em "armação_enviada_montagem"
    if ordem.status != 'armação_enviada_montagem':
        flash('Apenas OS com armação enviada podem registrar quebra.', 'warning')
        return redirect(url_for('caixa.monitor_producao'))
    
    if request.method == 'POST':
        observacao = request.form.get('observacao', '').strip()
        if not observacao:
            flash('Informe o motivo da quebra.', 'danger')
            return redirect(request.url)
        
        # Atualiza status e observação
        ordem.status = 'devolucao_quebra_armação'
        ordem.observacao_devolucao = observacao
        db.session.commit()
        flash('Quebra de armação registrada com sucesso!', 'success')
        return redirect(url_for('caixa.monitor_producao'))
    
    return render_template('caixa/quebra_armação.html', ordem=ordem)

@bp.route('/os/<os_numero>/reativar-armação', methods=['POST'])
@login_required
def reativar_com_nova_armação(os_numero):
    """
    Reativa uma OS com quebra de armação, permitindo nova montagem.
    """
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    if ordem.status != 'devolucao_quebra_armação':
        flash('Apenas OS com quebra de armação podem ser reativadas.', 'warning')
        return redirect(url_for('caixa.monitor_producao'))
    
    # Volta para o status anterior à montagem
    ordem.status = 'servico_aguardando_armação'
    # Opcional: limpar observação antiga ou manter como histórico
    # ordem.observacao_devolucao = None  # ou mantém para histórico
    
    db.session.commit()
    flash(f'OS {os_numero} reativada para nova armação!', 'success')
    return redirect(url_for('caixa.monitor_producao'))

@bp.route('/os/<os_numero>/receber-servico', methods=['POST'])
@login_required
def receber_servico(os_numero):
    """Caixa recebe o serviço como pronto para entrega"""
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    if ordem.status != 'servico_montado_conferido':
        flash('Apenas serviços montados e conferidos podem ser recebidos.', 'warning')
        return redirect(url_for('caixa.monitor_producao'))
    
    ordem.status = 'servico_pronto_entrega'
    db.session.commit()
    flash('Serviço recebido e pronto para entrega!', 'success')
    return redirect(url_for('caixa.monitor_producao'))

@bp.route('/baixar-carne')
@login_required
def baixar_carne():
    # Aqui você pode buscar carnes do cliente e mostrar tela de baixa
    return render_template('caixa/baixar_carne.html')

@bp.route('/pesquisa-produtos')
@login_required
def pesquisa_produtos():
    # Tela de pesquisa de produtos
    return render_template('caixa/pesquisa_produtos.html')

@bp.route('/historico-vendas')
@login_required
def historico_vendas():
    """Exibe histórico de vendas (CVs e OSs) para o caixa"""
    # Simulando dados — substitua por query real depois
    vendas = [
        {
            'cv': 1025,
            'os': '0100123',
            'cliente': 'Maria Oliveira',
            'data': '03/01/2026',
            'total': '890,00',
            'status': 'Concluída'
        },
        {
            'cv': 1024,
            'os': '0100122',
            'cliente': 'João Silva',
            'data': '02/01/2026',
            'total': '1.250,00',
            'status': 'Em produção'
        }
    ]
    return render_template('caixa/historico_vendas.html', vendas=vendas)

@bp.route('/devolucao', methods=['GET', 'POST'])
@login_required
def devolucao():
    cv_numero = None
    itens = []
    erro = None

    if request.method == 'POST':
        cv_numero = request.form.get('cv_numero')
        if cv_numero:
            # Busca OS com essa CV
            os = OrdemServico.query.filter_by(cv_numero=cv_numero).first()
            if os:
                # Busca itens da CV (substitua pela sua lógica real)
                itens = ItemVenda.query.filter_by(cv_numero=cv_numero).all()
                if not itens:
                    erro = "Nenhum item encontrado para esta CV."
            else:
                erro = "CV não encontrada."

    return render_template('caixa/devolucao.html', 
                          cv_numero=cv_numero, 
                          itens=itens, 
                          erro=erro)

@bp.route('/devolucao/processar', methods=['POST'])
@login_required
def processar_devolucao():
    cv_numero = request.form.get('cv_numero')
    acao = request.form.get('acao')
    itens_selecionados = request.form.getlist('itens_devolucao')

    os = OrdemServico.query.filter_by(cv_numero=cv_numero).first_or_404()
    todos_itens = ItemVenda.query.filter_by(cv_numero=cv_numero).all()
    
    if acao == 'total':
        # Cancela tudo
        for item in todos_itens:
            devolver_item_ao_estoque(item)
            item.status = 'cancelado'
        os.status = 'cancelada'
        tipo_dev = 'total'
        valor_cred = sum(item.valor for item in todos_itens)
        itens_para_registro = todos_itens

    elif acao == 'parcial':
        if not itens_selecionados:
            flash('Nenhum item selecionado.', 'warning')
            return redirect(url_for('caixa.devolucao'))
        itens_dev = ItemVenda.query.filter(ItemVenda.id.in_(itens_selecionados)).all()
        for item in itens_dev:
            devolver_item_ao_estoque(item)
            item.status = 'devolvido'
        tipo_dev = 'parcial'
        valor_cred = sum(item.valor for item in itens_dev)
        itens_para_registro = itens_dev

    # ✅ REGISTRA A DEVOLUÇÃO
    devolucao = Devolucao(
        cv_numero=cv_numero,
        cliente_id=os.cliente_id,
        tipo=tipo_dev,
        valor_credito=valor_cred,
        usuario_id=current_user.us_reg,
        observacao=request.form.get('observacao', '')
    )
    db.session.add(devolucao)
    db.session.flush()  # para pegar o ID

    # Itens da devolução
    for item in itens_para_registro:
        item_dev = ItemDevolucao(
            devolucao_id=devolucao.id,
            item_venda_id=item.id,
            tipo_item=item.tipo,
            descricao=item.descricao,
            valor=item.valor
        )
        db.session.add(item_dev)

    db.session.commit()
    flash(f'Devolução ({tipo_dev}) registrada com sucesso!', 'success')
    return redirect(url_for('caixa.index'))

def devolver_item_ao_estoque(item):
    """Lógica para devolver item ao estoque com base no tipo"""
    if item.tipo == 'armação':
        # Atualiza estoque de armação (ex: produto.estoque += 1)
        produto = Produto.query.get(item.produto_id)
        if produto:
            produto.estoque = (produto.estoque or 0) + 1
    
    elif item.tipo in ['lente_direita', 'lente_esquerda']:
        # Zera produção de lente (ou marca como cancelada)
        # Ex: atualiza status na OS ou em tabela de produção
        pass

@bp.route('/cancelar-cupon')
@login_required
def cancelar_cupon():
    print("✅ Rota /cancelar-cupon foi chamada!")  # ← DEBUG
    if not (current_user.us_email=='master@system' ):
        flash('Acesso negado. Apenas administradores podem cancelar cupons.', 'danger')
        return redirect(url_for('caixa.index'))
    
    notas = []  # temporário
    return render_template('caixa/cancelar_cupon.html', notas=notas)

@bp.route('/nova-venda-os', methods=['GET', 'POST'])
@login_required
def nova_venda_os():
    ultima_os = OrdemServico.query.order_by(OrdemServico.os_numero.desc()).first()
    proximo_numero = (ultima_os.os_numero + 1) if ultima_os else 1

    # 🔽 LÓGICA SEGURA DE AMBIENTE 🔽
    vendedor_automatico = None
    vendedores_lista = []

    # Só preenche automaticamente se:
    # - tem ambiente definido
    # - e o ambiente é 'vendedor'
    if (current_user.us_ambiente_id is not None and
        current_user.ambiente and
        current_user.ambiente.amb_nome == 'vendedor'):
        vendedor_automatico = current_user.us_reg
    else:
        # Inclui: 
        # - usuários sem ambiente (ex: ProgramadorMaster)
        # - usuários de outros ambientes (ex: Caixa, Admin)
        vendedores_lista = Usuario.query.filter_by(us_ativo=True).all()

    if request.method == 'POST':
        os_numero = int(request.form.get('os_numero', proximo_numero))
        cliente_id = request.form.get('cliente_id') or None
        vendedor_id = vendedor_automatico or request.form.get('vendedor_id') or None
        convenio_id = request.form.get('convenio_id') or None
        laboratorio_id = request.form.get('laboratorio_id') or None
        medico_id = request.form.get('medico_id') or None
        data_emissao = request.form.get('data_emissao')

        nova_os = OrdemServico(
            os_numero=os_numero,
            cliente_id=cliente_id,
            vendedor_id=vendedor_id,
            convenio_id=convenio_id,
            laboratorio_id=laboratorio_id,
            medico_id=medico_id,
            data_emissao=data_emissao,
            status='aberta'
        )
        db.session.add(nova_os)
        db.session.commit()

        flash('Ordem de serviço criada com sucesso!', 'success')
        return redirect(url_for('caixa.monitor_producao'))

    # Carrega outras listas
    convenios = []
    laboratorios = []
    medicos = []
    try:
        convenios = Convenio.query.all()
        laboratorios = Laboratorio.query.all()
        medicos = Medico.query.all()
    except:
        pass

    return render_template('caixa/nova_venda_os.html',
                         proximo_numero=proximo_numero,
                         vendedor_automatico=vendedor_automatico,
                         vendedores_lista=vendedores_lista,
                         convenios=convenios,
                         laboratorios=laboratorios,
                         medicos=medicos,
                         hoje=date.today())

@bp.route('/buscar-cliente')
@login_required
def buscar_cliente():
    termo = request.args.get('termo', '').strip()
    tipo = request.args.get('tipo', 'nome')

    cliente = None
    if tipo == 'cpf':
        cliente = Cadastro.query.filter(Cadastro.cpf_cnpj.like(f"%{termo}%")).first()
    elif tipo == 'codigo':
        cliente = Cadastro.query.filter(Cadastro.codigo.like(f"%{termo}%")).first()
    else:  # nome
        cliente = Cadastro.query.filter(Cadastro.nome.ilike(f"%{termo}%")).first()

    if cliente:
        return {
            'cliente': {
                'id': cliente.id,
                'nome': cliente.nome,
                'cpf_cnpj': cliente.cpf_cnpj,
                'codigo': cliente.codigo
            }
        }
    return {'cliente': None}

@bp.route('/buscar-item-venda')
@login_required
def buscar_item_venda():
    codigo = request.args.get('codigo', '').strip()
    if not codigo or len(codigo) != 7:
        return {'item': None, 'erro': 'Código deve ter exatamente 7 dígitos'}

    primeiro_digito = codigo[0]

    # 👇 SERVIÇO: começa com '2'
    if primeiro_digito == '2':
        servico = Produto.query.filter_by(
            prod_codigo_barras=codigo,
            prod_tipo='servico'
        ).first()
        if servico:
            return {
                'item': {
                    'id': servico.prod_reg,
                    'codigo': servico.prod_codigo_barras,
                    'descricao': servico.prod_descricao_servico or servico.prod_nome,
                    'valor_venda': float(servico.prod_preco_custo),
                    'tipo': 'servico',
                    'saldo': 0,
                    'reserva': 0
                }
            }
        else:
            return {'item': None, 'erro': 'Serviço não encontrado'}

    # 👇 ARMAÇÃO: começa com '1'
    elif primeiro_digito == '1':
        armacao = Produto.query.filter_by(
            prod_codigo_barras=codigo,
            prod_tipo='armacao'
        ).first()
        if armacao:
            saldo = getattr(armacao, 'prod_estoque', 0)
            reserva = getattr(armacao, 'prod_reserva', 0)
            return {
                'item': {
                    'id': armacao.prod_reg,
                    'codigo': armacao.prod_codigo_barras,
                    'descricao': f"{armacao.prod_nome} ({armacao.prod_tipo_aramacao or ''})",
                    'valor_venda': float(armacao.prod_preco_custo),
                    'tipo': 'armação',
                    'saldo': max(0, int(saldo)),
                    'reserva': int(reserva)
                }
            }
        else:
            return {'item': None, 'erro': 'Armação não encontrada'}

    # 👇 LENTE GENÉRICA: começa com '0'
    elif primeiro_digito == '0':
        lente = LenteGenerica.query.filter_by(codigo_base=codigo).first()
        if lente:
            return {
                'item': {
                    'id': lente.id,
                    'codigo': lente.codigo_base,
                    'descricao': lente.descricao,
                    'valor_venda': float(lente.preco_base),
                    'tipo': 'lente',
                    'saldo': 0,
                    'reserva': 0
                }
            }
        else:
            return {'item': None, 'erro': 'Lente genérica não encontrada'}

    # 👇 Código inválido (não começa com 0, 1 ou 2)
    else:
        return {'item': None, 'erro': 'Código inválido. Use: 0=lente, 1=armação, 2=serviço'}

#----- GARANTIA -----    

@bp.route('/registrar-garantia', methods=['POST'])
@login_required
def registrar_garantia():
    data = request.get_json()
    cv_numero = data['cv_numero']
    itens = data['itens']
    armacao_na_loja = data.get('armacao_na_loja')

    # 1. Busca a venda original (CV)
    cv = ComandaVenda.query.filter_by(numero=cv_numero).first_or_404()

    # 2. Gera novo número de OS para garantia (ex: 1GR, 2GR)
    ultima_gr = OrdemServico.query.filter(OrdemServico.os_numero.like('%GR')).order_by(OrdemServico.id.desc()).first()
    if ultima_gr:
        num = int(ultima_gr.os_numero.replace('GR', '')) + 1
    else:
        num = 1
    nova_os_numero = f"{num}GR"

    # 3. Cria nova OS de garantia
    nova_os = OrdemServico(
        os_numero=nova_os_numero,
        cliente_id=cv.cliente_id,
        vendedor_id=cv.vendedor_id,
        laboratorio_id=cv.laboratorio_id,
        medico_id=cv.medico_id,
        data_emissao=date.today(),
        data_prevista_cliente=cv.data_prevista_cliente,
        status='garantia',
        tipo='garantia'
    )
    db.session.add(nova_os)
    db.session.flush()  # para obter o ID

    # 4. Processa itens
    for item in itens:
        # Adiciona item à nova OS
        item_os = ItemOS(
            os_id=nova_os.id,
            produto_id=item['id'],
            defeito=item['defeito'],
            par_completo=item.get('par_completo'),
            tipo=item['tipo']
        )
        db.session.add(item_os)

        # Se for armação e ficou na loja → devolve ao estoque
        if item['tipo'] == 'armação' and armacao_na_loja:
            produto = Produto.query.get(item['id'])
            if produto:
                produto.prod_estoque += 1
                db.session.add(produto)

    db.session.commit()

    return jsonify({
        'success': True,
        'nova_os': nova_os_numero
    })

@bp.route('/buscar-os-por-cv')
@login_required
def buscar_os_por_cv():
    cv = request.args.get('cv', '').strip()
    if not cv:
        return jsonify({'error': 'CV não fornecida'})

    # Busca a OS pela CV (supondo que você tenha um campo `cv_numero` na tabela)
    os = OrdemServico.query.filter_by(cv_numero=cv).first()
    if not os:
        return jsonify({'error': f'OS não encontrada para CV "{cv}"'})

    # Carrega cliente, vendedor, laboratório, médico
    cliente = os.cliente if os.cliente else None
    vendedor = os.vendedor if os.vendedor else None
    laboratorio = os.laboratorio if os.laboratorio else None
    medico = os.medico if os.medico else None

    # Carrega itens da OS (produtos e serviços)
    itens = []
    # Supondo que você tem uma relação `os.itens` ou algo similar
    # Ajuste conforme seu modelo
    for item in os.itens:  # <-- isso depende do seu modelo!
        itens.append({
            'id': item.id,
            'descricao': item.produto.descricao if hasattr(item, 'produto') else item.servico.nome,
            'tipo': 'armação' if hasattr(item, 'produto') and item.produto.prod_tipo == 'armacao' else 'lente' if hasattr(item, 'produto') else 'servico'
        })

    return jsonify({
        'os': {
            'os_numero': os.os_numero,
            'data_emissao': str(os.data_emissao),
            'data_prevista_cliente': str(os.data_prevista_cliente) if os.data_prevista_cliente else None
        },
        'cliente': {'cli_nome': cliente.cli_nome} if cliente else {},
        'vendedor': {'us_cad': vendedor.us_cad} if vendedor else {},
        'laboratorio': {'lab_nome': laboratorio.lab_nome} if laboratorio else {},
        'medico': {'med_nome': medico.med_nome, 'med_crm': medico.med_crm} if medico else {},
        'itens': itens
    })

@bp.route('/vendas')
@login_required
def vendas_do_dia():
    hoje = date.today()
    
    # Busca todas as OS do dia (com status 'venda_concluida' ou similar)
    ordens = OrdemServico.query.filter(
        OrdemServico.data_emissao >= hoje,
        OrdemServico.data_emissao < hoje + timedelta(days=1),
        OrdemServico.status == 'venda_concluida'
    ).order_by(OrdemServico.os_numero.desc()).all()

    # Calcula total do dia
    total_dia = sum(o.total_compra for o in ordens if o.total_compra)

    return render_template('caixa/vendas_do_dia.html', 
                         ordens=ordens, 
                         total_dia=total_dia,
                         hoje=hoje)

@bp.route('/devolucoes')
@login_required
def devolucoes_do_dia():
    hoje = date.today()
    
    # Ajuste conforme seu modelo de Devolução
    devolucoes = Devolucao.query.filter(
        Devolucao.data_devolucao >= hoje,
        Devolucao.data_devolucao < hoje + timedelta(days=1)
    ).order_by(Devolucao.id.desc()).all()

    total_devolucoes = sum(d.valor_devolucao or 0 for d in devolucoes)

    return render_template('caixa/devolucoes_do_dia.html',
                         devolucoes=devolucoes,
                         total_devolucoes=total_devolucoes,
                         hoje=hoje)

@bp.route('/garantias-do-dia')
@login_required
def garantias_do_dia():
    hoje = date.today()
    
    # Ajuste conforme seu modelo de Garantia
    garantias = OrdemServico.query.filter(
        OrdemServico.data_emissao >= hoje,
        OrdemServico.data_emissao < hoje + timedelta(days=1),
        OrdemServico.status == 'garantia'
    ).order_by(OrdemServico.os_numero.desc()).all()

    total_garantias = len(garantias)

    return render_template('caixa/garantias_do_dia.html',
                         garantias=garantias,
                         total_garantias=total_garantias,
                         hoje=hoje)

from datetime import date, timedelta

@bp.route('/operacoes')
@login_required
def operacoes():
    return render_template('caixa/operacoes.html')

@bp.route('/ordens-servico')
@login_required
def ordens_servico():
    # Filtros
    data_de = request.args.get('data_de', '')
    data_ate = request.args.get('data_ate', '')
    nome_cliente = request.args.get('nome_cliente', '').strip()

    query = OrdemServico.query.filter(
        OrdemServico.status.in_(['venda_concluida', 'liberado_compra', 'servico_montado_conferido', 'servico_pronto_entrega'])
    )

    if data_de:
        query = query.filter(OrdemServico.data_emissao >= date.fromisoformat(data_de))
    if data_ate:
        query = query.filter(OrdemServico.data_emissao <= date.fromisoformat(data_ate))
    if nome_cliente:
        query = query.join(Cliente).filter(Cliente.cli_nome.ilike(f'%{nome_cliente}%'))

    ordens = query.order_by(OrdemServico.os_numero.desc()).all()

    # Calcular situação e cor
    for os in ordens:
        if os.data_prevista_cliente:
            dias_restantes = (os.data_prevista_cliente - date.today()).days
            if dias_restantes > 5:
                os.situacao_cor = 'success'  # verde
            elif dias_restantes > 2:
                os.situacao_cor = 'warning'  # amarelo
            else:
                os.situacao_cor = 'danger'   # vermelho
        else:
            os.situacao_cor = 'secondary'

    return render_template('caixa/ordens_servico.html',
                         ordens=ordens,
                         data_de=data_de,
                         data_ate=data_ate,
                         nome_cliente=nome_cliente)


@bp.route('/receita', methods=['GET', 'POST'])
@login_required
def receita():
    os_numero = request.args.get('os_numero')
    produto_id = request.args.get('produto_id')

    if not os_numero or not produto_id:
        flash('Dados insuficientes para gerar receita.', 'warning')
        return redirect(url_for('caixa.index'))

    # Busca OS e produto
    os = OrdemServico.query.filter_by(os_numero=os_numero).first_or_404()
    produto = Produto.query.get(produto_id)

    if not produto or produto.prod_tipo != 'lente':
        flash('Produto não é uma lente.', 'danger')
        return redirect(url_for('caixa.visualizar_os', os_numero=os_numero))

    # Inicializa estrutura da receita
    receita = {
        'cliente': os.cliente.cli_nome if os.cliente else '-',
        'paciente': os.cliente.cli_nome if os.cliente else '-',
        'medico': os.medico.med_nome if os.medico else '-',
        'crm': os.medico.med_crm if os.medico else '-',
        'data_aviso': date.today().strftime('%d/%m/%Y'),
        'lente_generica': produto.descricao,
        'dioptria_od': {
            'esf': '',
            'cil': '',
            'eixo': '',
            'adicao': '',
            'co': ''
        },
        'dioptria_oe': {
            'esf': '',
            'cil': '',
            'eixo': '',
            'adicao': '',
            'co': ''
        },
        'dp': {
            'longe': '',
            'perto': '',
            'olho_dominante': 'Nenhum'
        },
        'lente_digital': {
            'dist_vertice': '',
            'dist_pupilar': '',
            'pantoscopico': '',
            'curvatura': '',
            'he': '',
            'st': ''
        },
        'observacoes': ''
    }

    if request.method == 'POST':
        # Aqui você pode salvar os dados da receita no banco
        # Exemplo: criar um registro em uma tabela `Receita`
        
        flash('Receita salva com sucesso!', 'success')
        return redirect(url_for('caixa.visualizar_os', os_numero=os_numero))

    return render_template('caixa/receita.html',
                         os=os,
                         produto=produto,
                         receita=receita)