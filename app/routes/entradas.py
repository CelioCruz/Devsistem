from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from ..extensions import db
from ..models import *
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import os
import random
import string
import re

bp = Blueprint('entradas', __name__, url_prefix='/entradas')

def verificar_acesso():
    if not current_user.is_authenticated:
        return "Usuário não autenticado."
    # ✅ CERTO: permitir master OU usuários com ambiente "entradas"
    if hasattr(current_user, 'us_email') and current_user.us_email in {'cruz@devsoft', 'master@system'}:
        return None  # master tem acesso total
    # Verificar se o usuário tem acesso ao módulo "entradas"
    if hasattr(current_user, 'ambientes_permitidos'):
        nomes_ambientes = [amb.amb_nome for amb in current_user.ambientes_permitidos]
        if 'entradas' in nomes_ambientes:
            return None
    return "Você não tem permissão para acessar este módulo."

def str_to_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None

def eh_armacao_por_ncm(ncm: str) -> bool:
    ncm = ncm.replace('.', '').replace('-', '').strip()
    return ncm in ('90031100', '90041000')

def obter_tipo_aramacao(ncm: str) -> str:
    ncm = ncm.replace('.', '').replace('-', '').strip()
    return 'AR' if ncm == '90031100' else 'OC'

def gerar_codigo_armacao():
    prefixo = '1'
    ultimo = db.session.query(db.func.max(Produto.prod_codigo_barras)) \
        .filter(Produto.prod_codigo_barras.like(f"{prefixo}%")).scalar()
    num = int(ultimo[1:]) + 1 if ultimo else 1
    return f"{prefixo}{num:06d}"

def extrair_produtos_xml(filepath):
    produtos = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        raise Exception(f"Erro ao carregar XML: {str(e)}")

    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    for det in root.findall('.//nfe:det', ns):
        prod_elem = det.find('.//nfe:prod', ns)
        if prod_elem is None:
            continue  # pula itens sem elemento <prod>

        codigo = (prod_elem.find('nfe:cProd', ns).text if prod_elem.find('nfe:cProd', ns) is not None else '').strip()
        descricao = (prod_elem.find('nfe:xProd', ns).text if prod_elem.find('nfe:xProd', ns) is not None else '').strip()
        quantidade = float(prod_elem.find('nfe:qCom', ns).text) if prod_elem.find('nfe:qCom', ns) is not None else 0.0
        preco_unitario = float(prod_elem.find('nfe:vUnCom', ns).text) if prod_elem.find('nfe:vUnCom', ns) is not None else 0.0
        ncm_elem = prod_elem.find('nfe:NCM', ns)
        ncm = ncm_elem.text if ncm_elem is not None else ''

        produto_cadastrado = Produto.query.filter_by(prod_codigo_barras=codigo).first()
        produtos.append({
            'codigo': codigo,
            'descricao': descricao,
            'quantidade': quantidade,
            'preco_unitario': preco_unitario,
            'ncm': ncm,
            'cadastrado': produto_cadastrado is not None,
            'produto_id': produto_cadastrado.prod_reg if produto_cadastrado else None,
            'codigo_fornecedor': codigo
        })
    return produtos

def gerar_numero_ordem_compra():
    from datetime import datetime
    ano = datetime.now().year
    try:
        # Tenta obter o último número com lock
        ultima = OrdemCompra.query.with_for_update().filter(
            OrdemCompra.oc_numero.like(f'OC-{ano}-%')
        ).order_by(OrdemCompra.oc_reg.desc()).first()
        
        if ultima:
            ultimo_num = int(ultima.oc_numero.split('-')[-1])
            novo_num = ultimo_num + 1
        else:
            novo_num = 1
            
        return f'OC-{ano}-{novo_num:04d}'
    except Exception as e:
        db.session.rollback()
        raise e

# === ROTAS ===

@bp.route('/')
@login_required
def index():
    erro = verificar_acesso()
    if erro:
        return erro
    return render_template('entradas/index.html')

@bp.route('/entrada-nfe', methods=['GET', 'POST'])
@login_required
def entrada_nf():
    erro = verificar_acesso()
    if erro:
        return erro

    if request.method == 'POST':
        nf_chave = request.form.get('nf_chave', '').strip()
        xml_file = request.files.get('xml_file')

        if not nf_chave and not xml_file:
            flash('Informe a chave da NF-e ou selecione um XML.', 'warning')
            return render_template('entradas/entrada_nf.html')

        cabecalho = {}
        produtos_nf = []

        if nf_chave:
            if len(nf_chave) != 44:
                flash('Chave da NF-e deve ter 44 dígitos.', 'warning')
                return render_template('entradas/entrada_nf.html')
            
            fornecedor_cnpj = '12345678901234'
            armacao_ex = Produto.query.filter_by(prod_codigo_barras='1000001').first()
            lente_ex = Produto.query.filter_by(prod_codigo_barras='0123456').first()

            produtos_nf = [
                {
                    'codigo': '1000001',
                    'descricao': 'ARMAÇÃO PC6225 PRETO 52 19',
                    'quantidade': 5.0,
                    'preco_unitario': 89.90,
                    'ncm': '90031100',
                    'cadastrado': armacao_ex is not None,
                    'produto_id': armacao_ex.prod_reg if armacao_ex else None
                },
                {
                    'codigo': '0123456',
                    'descricao': 'LENTE OFTALMICA EXEMPLO',
                    'quantidade': 10.0,
                    'preco_unitario': 25.90,
                    'ncm': '90049000',
                    'cadastrado': lente_ex is not None,
                    'produto_id': lente_ex.prod_reg if lente_ex else None
                }
            ]

            cabecalho = {
                'nf_chave': nf_chave,
                'nf_numero': '12345',
                'serie': '1',
                'data_emissao': '2025-12-08',
                'fornecedor_cnpj': fornecedor_cnpj
            }

        elif xml_file and xml_file.filename:
            filepath = os.path.join('uploads', secure_filename(xml_file.filename))
            os.makedirs('uploads', exist_ok=True)
            xml_file.save(filepath)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    print("Conteúdo do XML (primeiros 500 chars):")
                    print(f.read()[:500])
            except Exception as e:
                print(f"Erro ao ler XML para debug: {e}")
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
                ide = root.find('.//nfe:ide', ns)
                emit = root.find('.//nfe:emit', ns)
                cabecalho = {
                    'nf_chave': 'XML',
                    'nf_numero': ide.find('nfe:nNF', ns).text if ide.find('nfe:nNF', ns) is not None else '',
                    'serie': ide.find('nfe:serie', ns).text if ide.find('nfe:serie', ns) is not None else '1',
                    'data_emissao': (ide.find('nfe:dhEmi', ns).text[:10] if ide.find('nfe:dhEmi', ns) is not None else datetime.now().strftime('%Y-%m-%d')),
                    'fornecedor_cnpj': (emit.find('nfe:CNPJ', ns).text if emit.find('nfe:CNPJ', ns) is not None else ''),
                    'nota_fiscal': 'recebida',
                    'tipo_nota': 'nfe',
                    'natureza_operacao': '1.102'
                }
                produtos_nf = extrair_produtos_xml(filepath)
            except Exception as e:
                flash(f'Erro ao processar XML: {str(e)}', 'danger')
                return render_template('entradas/entrada_nf.html')
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)

        session['entrada_temp'] = {
            'origem': 'xml' if xml_file else 'chave',
            'cabecalho': cabecalho,
            'produtos': produtos_nf
        }
        return render_template('entradas/conferir_entrada.html', dados=session['entrada_temp'])

    return render_template('entradas/entrada_nf.html')

@bp.route('/cadastrar-armacao/<int:item_id>', methods=['GET', 'POST'])
@login_required
def cadastrar_armacao(item_id):
    erro = verificar_acesso()
    if erro:
        return erro

    item = ItemEntrada.query.get_or_404(item_id)
    if item.produto_id:
        flash('Este item já está associado.', 'info')
        return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))

    if request.method == 'POST':
        # Gerar código único para armação (prefixo 1)
        prefixo = '1'
        ultimo = db.session.query(db.func.max(Produto.prod_codigo_barras)) \
            .filter(Produto.prod_codigo_barras.like(f"{prefixo}%")).scalar()
        num = int(ultimo[1:]) + 1 if ultimo else 1
        codigo = f"{prefixo}{num:06d}"

        # Obter dados do formulário
        tipo_aramacao = request.form.get('tipo_aramacao', 'AR')  # AR ou OC
        descricao_iniciais = request.form.get('descricao_iniciais', 'ARMA').upper()[:4]
        peca = request.form.get('peca', '').upper()
        cor = request.form.get('cor', '')
        tamanho = request.form.get('tamanho', '')
        ponte = request.form.get('ponte', '')
        preco_custo = item.preco_unitario

        # Montar descrição padronizada
        descricao_final = f"{tipo_aramacao} {descricao_iniciais} {peca} {cor} {tamanho} {ponte}".strip()

        # Criar produto
        produto = Produto(
            prod_codigo_barras=codigo,
            prod_nome=descricao_final,
            prod_empresa='Sistema',
            prod_preco_custo=preco_custo,
            prod_tipo='armacao',
            prod_fabricante_id=item.entrada.fornecedor_id,
            prod_ativo=True,
            prod_descricao_iniciais=descricao_iniciais,
            prod_tipo_aramacao=tipo_aramacao,
            prod_peca=peca,
            prod_cor=cor,
            prod_tamanho=tamanho,
            prod_ponte=ponte
        )
        db.session.add(produto)
        db.session.flush()

        # Associar ao item
        item.produto_id = produto.prod_reg
        db.session.commit()

        flash('Armação cadastrada e associada!', 'success')
        return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))

    return render_template('entradas/cadastrar_armacao.html', item=item)

@bp.route('/associar/<int:item_id>', methods=['GET', 'POST'])
@login_required
def associar_produto(item_id):
    item = ItemEntrada.query.get_or_404(item_id)
    if item.produto_id:
        flash('Este item já está associado.', 'info')
        return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))

    if request.method == 'POST':
        produto_id = request.form.get('produto_id')
        numero_pedido_fornecedor = request.form.get('numero_pedido_fornecedor', '').strip()

        if produto_id:
            produto = Produto.query.get(produto_id)
            if produto:
                item.produto_id = produto.prod_reg
                db.session.commit()
                flash('Produto associado com sucesso!', 'success')
                
                # 👇 NOVO: Se informou número do pedido, atualiza status
                if numero_pedido_fornecedor:
                    # Busca Pedido Interno com esse número no fornecedor
                    pedido = OrdemCompra.query.filter_by(
                        oc_numero_fornecedor=numero_pedido_fornecedor,
                        oc_status='rascunho'
                    ).first()
                    
                    if pedido:
                        # Marca pedido como recebido
                        pedido.oc_status = 'recebida'
                        
                        # Atualiza TODAS as OSs vinculadas
                        ordens = OrdemServico.query.filter_by(pedido_compra_id=pedido.oc_reg).all()
                        for os in ordens:
                            os.status = 'lente_recebida'
                        
                        db.session.commit()
                        flash(f'Pedido {numero_pedido_fornecedor} recebido! {len(ordens)} OS(s) atualizada(s).', 'success')
                    else:
                        flash(f'Nenhum pedido pendente encontrado com o número "{numero_pedido_fornecedor}".', 'warning')
                
                return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))
        
        flash('Selecione um produto válido.', 'danger')

    # ... (lógica de GET permanece igual)
    termo = request.args.get('q', '').strip()
    categoria = request.args.get('categoria', '')
    # ... (sua lógica de busca de produtos)
    return render_template('entradas/associar_produto.html', item=item, produtos=produtos, termo=termo, categoria=categoria)

@bp.route('/manual', methods=['GET', 'POST'])
@login_required
def entrada_manual():
    erro = verificar_acesso()
    if erro:
        return erro

    if request.method == 'POST':
        produtos_manuais = []
        codigos = request.form.getlist('codigo_produto')
        for i in range(len(codigos)):
            produtos_manuais.append({
                'codigo': codigos[i],
                'descricao': request.form.getlist('descricao_produto')[i],
                'quantidade': float(request.form.getlist('quantidade')[i]),
                'preco_unitario': float(request.form.getlist('preco_unitario')[i])
            })

        cabecalho = {
            'nf_numero': request.form.get('nf_numero', ''),
            'serie': request.form.get('serie', ''),
            'data_emissao': request.form.get('data_emissao'),
            'data_recebimento': request.form.get('data_recebimento'),
            'fornecedor_cnpj': request.form.get('fornecedor_id'),
            'nota_fiscal': request.form.get('nota_fiscal', 'recebida'),
            'tipo_nota': request.form.get('tipo_nota', 'conventional'),
            'natureza_operacao': request.form.get('natureza_operacao')
        }

        session['entrada_temp'] = {
            'origem': 'manual',
            'cabecalho': cabecalho,
            'produtos': produtos_manuais
        }
        return render_template('entradas/conferir_entrada.html', dados=session['entrada_temp'])

    fornecedores = Fornecedor.query.all()
    naturezas = NaturezaOperacao.query.all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('entradas/entrada_manual.html', fornecedores=fornecedores, naturezas=naturezas, today=today)

@bp.route('/confirmar_entrada', methods=['POST'])
@login_required
def confirmar_entrada():
    erro = verificar_acesso()
    if erro:
        return erro

    dados = session.get('entrada_temp')
    if not dados:
        flash('Nenhum dado de entrada encontrado.', 'danger')
        return redirect(url_for('entradas.index'))

    cabecalho = dados['cabecalho']
    produtos = dados['produtos']

    # Criar entrada
    entrada = Entrada(
        tipo=dados['origem'],
        descricao=f"Entrada via {dados['origem']}",
        nf_chave=cabecalho.get('nf_chave'),
        nf_numero=cabecalho.get('nf_numero'),
        serie=cabecalho.get('serie'),
        data_emissao=str_to_date(cabecalho.get('data_emissao')),
        data_recebimento=str_to_date(cabecalho.get('data_recebimento')),
        nota_fiscal=cabecalho.get('nota_fiscal'),
        tipo_nota=cabecalho.get('tipo_nota'),
        natureza_operacao=cabecalho.get('natureza_operacao'),
        fornecedor_id=cabecalho.get('fornecedor_cnpj'),
        usuario_id=current_user.us_reg
    )
    db.session.add(entrada)
    db.session.flush()

    # Criar itens SEM vínculo
    for prod in produtos:
        item = ItemEntrada(
            entrada_id=entrada.id,
            produto_id=None,  # ← SEMPRE NULL
            quantidade=int(float(prod.get('quantidade', 1) or 1)),
            preco_unitario=float(prod.get('preco_unitario', 0.0) or 0.0)
        )
        db.session.add(item)

    db.session.commit()
    session.pop('entrada_temp', None)
    return redirect(url_for('entradas.editar_entrada', entrada_id=entrada.id))

@bp.route('/editar/<int:entrada_id>')
@login_required
def editar_entrada(entrada_id):
    erro = verificar_acesso()
    if erro:
        return erro  # ← remova o '+'
    entrada = Entrada.query.get_or_404(entrada_id)
    return render_template('entradas/editar_entrada.html', entrada=entrada)

@bp.route('/ajustar_precos')
@login_required
def ajustar_precos():
    erro = verificar_acesso()
    if erro:
        return erro
    dados = session.get('entrada_temp', {})
    return render_template('entradas/ajustar_precos.html', dados=dados)

@bp.route('/inventario')
@login_required
def inventario():
    erro = verificar_acesso()
    if erro:
        return erro
    produtos = Produto.query.all()
    return render_template('entradas/inventario.html', produtos=produtos)

@bp.route('/relatorio_cadastros_automaticos')
@login_required
def relatorio_cadastros_automaticos():
    erro = verificar_acesso()
    if erro:
        return erro
    cadastros = CadastroAutomatico.query.order_by(CadastroAutomatico.data_cadastro.desc()).all()
    return render_template('entradas/relatorio_cadastros.html', cadastros=cadastros)

def gerar_codigo_pedido():
    ultimo = db.session.query(db.func.max(Pedido.ped_codigo)).scalar()
    return f"PD{(int(ultimo[2:]) + 1) if ultimo else 1:04d}"

@bp.route('/devolucao_nf', methods=['GET', 'POST'])
@login_required
def devolucao_nf():
    erro = verificar_acesso()
    if erro:
        return erro

    if request.method == 'POST':
        nf_chave = request.form.get('nf_chave_original')
        entrada_original = Entrada.query.filter_by(nf_chave=nf_chave).first()
        if not entrada_original:
            flash('NF-e de entrada não encontrada.', 'danger')
            return redirect(url_for('entradas.entrada_nf'))

        pedido = Pedido(
            ped_codigo=gerar_codigo_pedido(),
            ped_tipo='saida',
            ped_descricao=f'Devolução NF-e {nf_chave}',
            ped_status='aberto',
            usuario_id=current_user.us_reg,
            cliente_id=entrada_original.fornecedor_id,
            nf_referencia=nf_chave
        )
        db.session.add(pedido)
        db.session.flush()

        for item_entrada in entrada_original.itens:
            if str(item_entrada.id) in request.form.getlist('devolver_item'):
                # 👇 Este bloco DEVE estar dentro do 'if POST' e dentro da função
                item_pedido = ItemPedido(
                    ped_id=pedido.ped_id,
                    prod_codigo=item_entrada.produto.prod_codigo_barras,  # ✅ Correto
                    prod_nome=item_entrada.produto.prod_nome,
                    prod_empresa='Sistema',
                    item_quantidade_solicitada=item_entrada.quantidade,
                    cfop='5403',
                    icms_origem='0',
                    icms_situacao='102',
                    ipi_situacao='99'
                )
                db.session.add(item_pedido)

        try:
            db.session.commit()
            flash('Pedido de devolução criado!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'danger')
        return redirect(url_for('entradas.index'))

    nf_chave = request.args.get('nf_chave')
    entrada = Entrada.query.filter_by(nf_chave=nf_chave).first_or_404()
    return render_template('entradas/confirmar_devolucao.html', nf_chave=nf_chave, entrada=entrada)

@bp.route('/pesquisa/<tipo>')
@login_required
def pesquisa(tipo):
    if tipo == 'cliente':
        clientes = Cliente.query.all()  
        return render_template(
            'admin/clientes.html',   
            clientes=clientes,
            origem='entradas',        
            modo_pesquisa=True        
        )
    erro = verificar_acesso()
    if erro:
        return erro

    query = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', 'produto')

    if tipo == 'produto':
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
        return render_template('admin/pesquisa_produto.html', produtos=produtos, origem='entradas')
    
    if tipo == 'fornecedor':
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
        return render_template('admin/pesquisa_fornecedor.html', fornecedores=fornecedores, origem='entradas')
    
    flash('Tipo de pesquisa inválido.', 'danger')
    return redirect(url_for('entradas.index'))


@bp.route('/ordens-compra')
@login_required
def listar_ordens_compra():
    ordens = OrdemCompra.query.all()
    return render_template('entradas/ordens_compra.html', ordens=ordens)

@bp.route('/ordens-compra/nova', methods=['GET', 'POST'])
@login_required
def nova_ordem_compra():
    if request.method == 'POST':
        # 👇 GERA O NÚMERO DE ORDEM DE COMPRA ÚNICO
        numero_oc = gerar_numero_ordem_compra()  # ← função que vamos definir abaixo
        
        ordem = OrdemCompra(
            oc_numero=numero_oc,  # ← campo obrigatório
            oc_empresa_id=request.form.get('oc_empresa_id', type=int),
            oc_fornecedor_id=request.form.get('oc_fornecedor_id', type=int),
            oc_data_emissao=request.form.get('oc_data_emissao'),
            oc_data_previsao=request.form.get('oc_data_previsao'),
            oc_condicao_pagamento=request.form.get('oc_condicao_pagamento'),
            oc_valor_frete=float(request.form.get('oc_valor_frete', '0')),
            oc_empresa_responsavel_id=request.form.get('oc_empresa_responsavel_id', type=int),
            oc_transportadora=request.form.get('oc_transportadora'),
            oc_entrega=request.form.get('oc_entrega'),
            oc_transporte=request.form.get('oc_transporte'),
            oc_etiquetagem=request.form.get('oc_etiquetagem'),
            oc_observacoes=request.form.get('oc_observacoes'),
            oc_status='rascunho',
            oc_usuario_criacao_id=current_user.us_reg
        )
        db.session.add(ordem)
        db.session.flush()
        
        # Processar itens (se houver)
        # ... (veremos abaixo)
        
        db.session.commit()
        flash(f'Ordem de Compra #{numero_oc} criada!', 'success')  # ← usa o número gerado
        return redirect(url_for('entradas.editar_ordem_compra', ordem_id=ordem.oc_reg))
    
    return render_template('entradas/ordem_compra_form.html')

@bp.route('/ordens-compra/editar/<int:ordem_id>', methods=['GET', 'POST'])
def editar_ordem_compra(ordem_id):
    ordem = OrdemCompra.query.get_or_404(ordem_id)
    
    if request.method == 'POST':
        # Atualizar dados
        ordem.oc_empresa_id = request.form.get('oc_empresa_id', type=int)
        ordem.oc_fornecedor_id = request.form.get('oc_fornecedor_id', type=int)
        ordem.oc_data_emissao = request.form.get('oc_data_emissao')
        ordem.oc_data_previsao = request.form.get('oc_data_previsao')
        ordem.oc_condicao_pagamento = request.form.get('oc_condicao_pagamento')
        ordem.oc_valor_frete = float(request.form.get('oc_valor_frete', '0'))
        ordem.oc_empresa_responsavel_id = request.form.get('oc_empresa_responsavel_id', type=int)
        ordem.oc_transportadora = request.form.get('oc_transportadora')
        ordem.oc_entrega = request.form.get('oc_entrega')
        ordem.oc_transporte = request.form.get('oc_transporte')
        ordem.oc_etiquetagem = request.form.get('oc_etiquetagem')
        ordem.oc_observacoes = request.form.get('oc_observacoes')
        
        # Processar itens (atualização ou adição)
        # ... (veremos abaixo)
        
        db.session.commit()
        flash(f'Ordem de Compra #{ordem.oc_numero} atualizada!', 'success')
        return redirect(url_for('entradas.editar_ordem_compra', ordem_id=ordem_id))
    
    return render_template('entradas/ordem_compra_form.html', ordem=ordem)

@bp.route('/ordens-compra/aprovar/<int:ordem_id>', methods=['POST'])
def aprovar_ordem_compra(ordem_id):
    ordem = OrdemCompra.query.get_or_404(ordem_id)
    
    if ordem.oc_status != 'rascunho':
        flash('Ordem já foi aprovada ou cancelada.', 'danger')
        return redirect(url_for('entradas.editar_ordem_compra', ordem_id=ordem_id))
    
    # Gerar Pedido de Entrada
    pedido_entrada = Entrada(
        ent_numero=gerar_proximo_codigo('entrada'),
        ent_fornecedor_id=ordem.oc_fornecedor_id,
        ent_data_emissao=ordem.oc_data_emissao,
        ent_data_recebimento=ordem.oc_data_previsao,
        ent_condicao_pagamento=ordem.oc_condicao_pagamento,
        ent_valor_frete=ordem.oc_valor_frete,
        ent_empresa_responsavel_id=ordem.oc_empresa_responsavel_id,
        ent_transportadora=ordem.oc_transportadora,
        ent_entrega=ordem.oc_entrega,
        ent_transporte=ordem.oc_transporte,
        ent_etiquetagem=ordem.oc_etiquetagem,
        ent_observacoes=ordem.oc_observacoes,
        ent_status='aberta',
        ent_usuario_criacao_id=current_user.us_reg
    )
    db.session.add(pedido_entrada)
    db.session.flush()
    
    # Copiar itens da ordem para a entrada
    for item_ordem in ordem.itens:
        item_entrada = ItemEntrada(
            ite_entrada_id=pedido_entrada.ent_reg,
            ite_produto_id=item_ordem.ioc_produto_id,
            ite_codigo_barras=item_ordem.ioc_codigo_barras,
            ite_descricao=item_ordem.ioc_descricao,
            ite_quantidade=item_ordem.ioc_quantidade,
            ite_unidade=item_ordem.ioc_unidade,
            ite_valor_unitario=item_ordem.ioc_valor_unitario,
            ite_peso=item_ordem.ioc_peso,
            ite_total=item_ordem.ioc_total
        )
        db.session.add(item_entrada)
    
    # Atualizar status da ordem
    ordem.oc_status = 'aprovada'
    
    db.session.commit()
    flash(f'Pedido de Entrada #{pedido_entrada.ent_numero} gerado a partir da Ordem de Compra #{ordem.oc_numero}!', 'success')
    return redirect(url_for('entradas.listar_entradas'))

@bp.route('/os/<os_numero>/compra', methods=['GET', 'POST'])
@login_required
def iniciar_compra_os(os_numero):
    """Permite ao estoque informar fornecedor e número do pedido para uma OS"""
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    # Só permite se estiver em "liberado_compra"
    if ordem.status != 'liberado_compra':
        flash('Esta OS não está liberada para compra.', 'warning')
        return redirect(url_for('entradas.index'))
    
    if request.method == 'POST':
        fornecedor_id = request.form.get('fornecedor_id')
        numero_pedido_fornecedor = request.form.get('numero_pedido_fornecedor', '').strip()
        
        if not fornecedor_id or not numero_pedido_fornecedor:
            flash('Preencha fornecedor e número do pedido.', 'danger')
            return redirect(request.url)
        
        # Cria Pedido Interno de Compra (reutiliza sua lógica)
        novo_pedido = OrdemCompra(
            oc_numero=gerar_numero_ordem_compra(),  # sua função existente
            oc_fornecedor_id=fornecedor_id,
            oc_numero_fornecedor=numero_pedido_fornecedor,
            oc_data_emissao=datetime.utcnow().date(),
            oc_data_previsao=datetime.utcnow().date(),
            oc_status='rascunho',
            oc_usuario_criacao_id=current_user.us_reg
        )
        db.session.add(novo_pedido)
        db.session.flush()  # para obter oc_reg
        
        # Atualiza a OS
        ordem.fornecedor_id = fornecedor_id
        ordem.numero_pedido_fornecedor = numero_pedido_fornecedor
        ordem.pedido_compra_id = novo_pedido.oc_reg
        ordem.status = 'aguardando_lentes'
        
        db.session.commit()
        flash(f'Pedido interno #{novo_pedido.oc_numero} criado. Aguardando NF com pedido {numero_pedido_fornecedor}.', 'success')
        return redirect(url_for('entradas.listar_os_liberadas'))
    
    # GET: mostra formulário
    fornecedores = Fornecedor.query.filter_by(forn_ativo=True).all()
    return render_template('entradas/iniciar_compra_os.html', ordem=ordem, fornecedores=fornecedores)

@bp.route('/os/liberadas')
@login_required
def listar_os_liberadas():
    """Lista todas as OS com status 'liberado_compra'"""
    ordens = OrdemServico.query.filter_by(status='liberado_compra').all()
    return render_template('entradas/lista_os_liberadas.html', ordens=ordens)

@bp.route('/os/<os_numero>/finalizar', methods=['GET', 'POST'])
@login_required
def finalizar_os(os_numero):
    """
    Permite atualizar o status da OS após 'Lente Recebida'.
    Para devolução, redireciona para tela de observação.
    """
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    if ordem.status != 'lente_recebida':
        flash('Apenas OS com status "Lente Recebida" podem ser finalizadas.', 'warning')
        return redirect(url_for('entradas.listar_os_finalizacao'))

    if request.method == 'POST':
        acao = request.form.get('acao')
        
        if acao == 'montagem':
            ordem.status = 'servico_enviado_montagem'
            db.session.commit()
            flash('Status atualizado: Serviço enviado para montagem.', 'success')
            return redirect(url_for('entradas.listar_os_finalizacao'))
            
        elif acao == 'aguardando_armação':
            ordem.status = 'servico_aguardando_armação'
            ordem.data_alerta_armação = datetime.utcnow()
            db.session.commit()
            flash('Status atualizado: Aguardando armação para montagem.', 'success')
            return redirect(url_for('entradas.listar_os_finalizacao'))
            
        elif acao == 'devolucao':
            # 👉 Redireciona para tela dedicada de observação (recomendado)
            return redirect(url_for('entradas.registrar_devolucao', os_numero=os_numero))
            
        else:
            flash('Ação inválida.', 'danger')
            return redirect(request.url)
    
    return render_template('entradas/finalizar_os.html', ordem=ordem)

@bp.route('/os/finalizacao')
@login_required
def listar_os_finalizacao():
    """Lista OS com status 'lente_recebida' (prontas para finalização)"""
    ordens = OrdemServico.query.filter_by(status='lente_recebida').all()
    return render_template('entradas/lista_os_finalizacao.html', ordens=ordens)

@bp.route('/os/<os_numero>/devolucao', methods=['GET', 'POST'])
@login_required
def registrar_devolucao(os_numero):
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    # Só permite se ainda está em "lente_recebida"
    if ordem.status != 'lente_recebida':
        flash('Esta OS não está em status de devolução.', 'warning')
        return redirect(url_for('entradas.listar_os_finalizacao'))
    
    if request.method == 'POST':
        observacao = request.form.get('observacao_devolucao', '').strip()
        if not observacao:
            flash('A observação é obrigatória para devoluções.', 'danger')
            return redirect(request.url)
        
        # Atualiza OS
        ordem.status = 'servico_devolvido_compra'
        ordem.observacao_devolucao = observacao
        db.session.commit()
        flash('Devolução registrada com sucesso!', 'success')
        return redirect(url_for('entradas.listar_os_finalizacao'))
    
    return render_template('entradas/devolucao_observacao.html', ordem=ordem)

@bp.route('/os/<os_numero>/liberar-compra', methods=['POST'])
@login_required
def liberar_compra_devolvida(os_numero):
    """
    Reativa uma OS devolvida, voltando ao status 'aguardando_lentes'
    SEM apagar dados de compra anteriores.
    """
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    if ordem.status != 'servico_devolvido_compra':
        flash('Apenas OS devolvidas podem ser reativadas.', 'warning')
        return redirect(url_for('entradas.listar_os_devolvidas'))
    
    # ✅ Mantém TUDO: fornecedor, número do pedido, etc.
    # Só muda o status de volta para o anterior
    ordem.status = 'aguardando_lentes'
    
    db.session.commit()
    flash(f'OS {os_numero} reativada para aguardar nova lente!', 'success')
    return redirect(url_for('entradas.listar_os_liberadas'))

@bp.route('/os/<os_numero>/conferir-montagem', methods=['POST'])
@login_required
def conferir_montagem(os_numero):
    """Estoque marca a OS como montada e conferida"""
    ordem = OrdemServico.query.get_or_404(os_numero)
    
    # Só permite se estiver em "armação_enviada_montagem" ou "reposicao_recebida"
    if ordem.status not in ['armação_enviada_montagem', 'reposicao_recebida']:
        flash('Apenas OS em montagem podem ser conferidas.', 'warning')
        return redirect(url_for('entradas.listar_os_montagem'))
    
    ordem.status = 'servico_montado_conferido'
    db.session.commit()
    flash('Serviço marcado como montado e conferido!', 'success')
    return redirect(url_for('entradas.listar_os_montagem'))