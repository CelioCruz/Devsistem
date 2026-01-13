from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import decimal
import os
import json
import gzip
# Extensões
from ..extensions import db
# Modelos (todos necessários)
from app.models.ambiente import Ambiente
from app.models.cliente import Cliente
from app.models.empresa import Empresa
from app.models.fornecedor import Fornecedor
from app.models.produto import Produto, LenteGenerica
from app.models.usuario import Usuario
from app.models.banco import Banco
from app.models.vendedor import Vendedor
from app.models.tipo_cartao import TipoCartao
from app.models.tipo_carne import TipoCarne
from app.models.operacao_conciliacao import OperacaoConciliacao
from app.models.feriado import Feriado
# Utils
from app.utils.cep import buscar_cep
from app.utils.codigos import gerar_proximo_codigo
from app.utils.lentes import gerar_combinacoes_lente

bp = Blueprint('admin', __name__, url_prefix='/admin')

# =============== HOME & MENU ===============
@bp.route('/home')
@login_required
def home():
    if hasattr(current_user, 'us_email') and current_user.us_email in ['cruz@devsoft', 'master@system']:
        return render_template('admin/programador.html')
    return render_template('home.html')

@bp.route('/cadastro')
@login_required
def cadastro():
    return render_template('admin/cadastro.html')

@bp.route('/gerencia')
@login_required
def gerencia():
    return render_template('admin/gerencia.html')

# =============== FUNÇÕES AUXILIARES ===============
def _tem_permissao_master():
    return hasattr(current_user, 'us_email') and current_user.us_email in ['cruz@devsoft', 'master@system']

def _tem_permissao():
    if _tem_permissao_master():
        return True
    if hasattr(current_user, 'us_tipo') and current_user.us_tipo == 'administrador':
        return True
    return False

# =============== USUÁRIOS ===============
@bp.route('/usuarios', methods=['GET', 'POST'])
@login_required
def listar_usuarios():
    if not _tem_permissao_master():
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))

    # Carregar listas fixas (usadas em GET e em caso de erro no POST)
    ambientes = Ambiente.query.filter_by(amb_ativo=True).all()
    empresas = Empresa.query.filter_by(emp_ativo=True).all()

    if request.method == 'POST':
        if 'excluir_usuario' in request.form:
            us_reg = request.form.get('us_reg', type=int)
            if us_reg:
                usuario = Usuario.query.get(us_reg)
                if usuario and usuario.us_email != 'cruz@devsoft':
                    db.session.delete(usuario)
                    db.session.commit()
                    flash(f'✅ Usuário "{usuario.us_cad}" excluído!', 'success')
                else:
                    flash('❌ Não é possível excluir o admin master.', 'danger')
        else:
            us_reg = request.form.get('us_reg', type=int)
            us_cad = request.form.get('us_cad', '').strip()
            us_email = request.form.get('us_email', '').strip()
            us_senha = request.form.get('us_senha', '')
            us_empresa_id = request.form.get('us_empresa_id', type=int)
            ambiente_ids = request.form.getlist('us_ambientes')
            ambiente_ids = [int(aid) for aid in ambiente_ids if aid.isdigit()]
            is_admin = us_email in {'cruz@devsoft', 'master@system'}

            if not us_cad or not us_email:
                flash('Nome e e-mail são obrigatórios.', 'warning')
            else:
                if us_reg:
                    usuario = Usuario.query.get(us_reg)
                    if not usuario:
                        flash('Usuário não encontrado.', 'danger')
                    elif Usuario.query.filter(Usuario.us_email == us_email, Usuario.us_reg != us_reg).first():
                        flash('E-mail já está em uso.', 'danger')
                    else:
                        usuario.us_cad = us_cad
                        usuario.us_email = us_email
                        usuario.us_empresa_id = us_empresa_id
                        if is_admin:
                            usuario.ambientes_permitidos = []
                        else:
                            ambientes_objs = Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
                            usuario.ambientes_permitidos = ambientes_objs
                        if us_senha:
                            usuario.us_senha = generate_password_hash(us_senha)
                        db.session.commit()
                        flash('Usuário atualizado!', 'success')
                        return redirect(url_for('admin.listar_usuarios'))
                else:
                    if Usuario.query.filter_by(us_email=us_email).first():
                        flash('E-mail já cadastrado.', 'danger')
                    else:
                        novo = Usuario(
                            us_cad=us_cad,
                            us_email=us_email,
                            us_senha=generate_password_hash(us_senha),
                            us_empresa_id=us_empresa_id
                        )
                        if is_admin:
                            novo.ambientes_permitidos = []
                        else:
                            ambientes_objs = Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
                            novo.ambientes_permitidos = ambientes_objs
                        db.session.add(novo)
                        db.session.commit()
                        flash('Usuário criado com sucesso!', 'success')
                        return redirect(url_for('admin.listar_usuarios'))

        # Se houver erro no POST, re-renderiza o formulário com os dados
        usuarios = Usuario.query.all()
        return render_template('admin/usuarios.html', usuarios=usuarios, ambientes=ambientes, empresas=empresas)

    # Método GET
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios, ambientes=ambientes, empresas=empresas)

@bp.route('/usuarios/toggle-ativo', methods=['POST'])
@login_required
def toggle_usuario_ativo():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    us_reg = request.form.get('us_reg')
    novo_status = request.form.get('ativo') == 'true'
    usuario = Usuario.query.get(us_reg)
    if usuario and usuario.us_email != 'cruz@devsoft':
        usuario.us_ativo = novo_status
        db.session.commit()
        flash(f'Usuário {"ativado" if novo_status else "desativado"}!', 'success')
    elif usuario and usuario.us_email == 'cruz@devsoft':
        flash('Não é possível desativar o master.', 'warning')
    return redirect(url_for('admin.listar_usuarios'))

# =============== EMPRESA ===============

@bp.route('/empresas')
@login_required
def listar_empresas():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    empresas = Empresa.query.all()
    return render_template('admin/empresas.html', empresas=empresas)

@bp.route('/empresas/nova', methods=['GET', 'POST'])
@login_required
def nova_empresa():
    if not _tem_permissao_master():
        flash('Somente o master pode criar empresas.', 'danger')
        return redirect(url_for('admin.listar_empresas'))

    # Carregar ambientes para o campo de seleção múltipla
    todos_ambientes = Ambiente.query.filter_by(amb_ativo=True).all()

    if request.method == 'POST':
        razao_social = request.form.get('emp_razao_social', '').strip()
        nome_fantasia = request.form.get('emp_nome_fantasia', '').strip()
        cnpj = request.form.get('emp_cnpj', '').strip()

        if not razao_social or not cnpj:
            flash('Razão Social e CNPJ são obrigatórios.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                todos_ambientes=todos_ambientes,
                **request.form  # mantém os dados no formulário
            )

        # Limpar CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ inválido.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                todos_ambientes=todos_ambientes,
                **request.form
            )

        if Empresa.query.filter_by(emp_cnpj=cnpj_limpo).first():
            flash('CNPJ já cadastrado.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                todos_ambientes=todos_ambientes,
                **request.form
            )

        # Criar empresa
        nova_empresa_obj = Empresa(
            emp_razao_social=razao_social,  # 👈 se seu modelo usa esse campo
            emp_nome_fantasia=nome_fantasia,
            emp_cnpj=cnpj_limpo,
            emp_ie=request.form.get('emp_ie', '').strip(),
            emp_im=request.form.get('emp_im', '').strip(),
            emp_cep=request.form.get('emp_cep', '').strip(),
            emp_endereco=request.form.get('emp_endereco', '').strip(),
            emp_bairro=request.form.get('emp_bairro', '').strip(),
            emp_cidade=request.form.get('emp_cidade', '').strip(),
            emp_uf=request.form.get('emp_uf', '').strip(),
            emp_telefone=request.form.get('emp_telefone', '').strip(),
            emp_email=request.form.get('emp_email', '').strip(),
            emp_ativo=True
        )
        db.session.add(nova_empresa_obj)
        db.session.flush()  # para obter o emp_reg

        # 👇 Opcional: associar ambientes (se o modelo suportar)
        # Se você tiver uma relação many-to-many entre Empresa e Ambiente
        # ambiente_ids = request.form.getlist('ambientes[]')
        # for amb_id in ambiente_ids:
        #     # adicionar na tabela associativa

        db.session.commit()
        flash(f'✅ Empresa "{razao_social}" cadastrada com sucesso!', 'success')
        return redirect(url_for('admin.listar_empresas'))

    return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes)

@bp.route('/empresas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_empresa(id):
    if not _tem_permissao_master():
        flash('Somente o master pode editar empresas.', 'danger')
        return redirect(url_for('admin.listar_empresas'))

    empresa = Empresa.query.get_or_404(id)
    todos_ambientes = Ambiente.query.filter_by(amb_ativo=True).all()

    if request.method == 'POST':
        empresa.emp_razao_social = request.form.get('emp_razao_social', '').strip()
        empresa.emp_nome_fantasia = request.form.get('emp_nome_fantasia', '').strip()
        cnpj = request.form.get('emp_cnpj', '').strip()

        if not empresa.emp_razao_social or not cnpj:
            flash('Razão Social e CNPJ são obrigatórios.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                empresa=empresa,
                todos_ambientes=todos_ambientes,
                **request.form
            )

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ inválido.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                empresa=empresa,
                todos_ambientes=todos_ambientes,
                **request.form
            )

        # Verificar duplicidade de CNPJ (exceto da própria empresa)
        outra = Empresa.query.filter(
            Empresa.emp_cnpj == cnpj_limpo,
            Empresa.emp_reg != empresa.emp_reg
        ).first()
        if outra:
            flash('CNPJ já cadastrado em outra empresa.', 'danger')
            return render_template(
                'admin/empresa_form.html',
                empresa=empresa,
                todos_ambientes=todos_ambientes,
                **request.form
            )

        empresa.emp_cnpj = cnpj_limpo
        empresa.emp_ie = request.form.get('emp_ie', '').strip()
        empresa.emp_im = request.form.get('emp_im', '').strip()
        empresa.emp_cep = request.form.get('emp_cep', '').strip()
        empresa.emp_endereco = request.form.get('emp_endereco', '').strip()
        empresa.emp_bairro = request.form.get('emp_bairro', '').strip()
        empresa.emp_cidade = request.form.get('emp_cidade', '').strip()
        empresa.emp_uf = request.form.get('emp_uf', '').strip()
        empresa.emp_telefone = request.form.get('emp_telefone', '').strip()
        empresa.emp_email = request.form.get('emp_email', '').strip()

        # 👇 Opcional: salvar ambientes permitidos (se implementar)
        # ambiente_ids = request.form.getlist('ambientes[]')
        # if ambiente_ids:
        #     ambientes_selecionados = Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
        #     empresa.ambientes_permitidos = ambientes_selecionados

        db.session.commit()
        flash(f'✅ Empresa "{empresa.emp_razao_social}" atualizada!', 'success')
        return redirect(url_for('admin.listar_empresas'))

    return render_template(
        'admin/empresa_form.html',
        empresa=empresa,
        todos_ambientes=todos_ambientes
    )

@bp.route('/empresas/toggle-ativo', methods=['POST'])
@login_required
def toggle_empresa_ativo():
    if not _tem_permissao_master():
        flash('Somente o master pode alterar o status de empresas.', 'danger')
        return redirect(url_for('admin.listar_empresas'))

    emp_reg = request.form.get('emp_reg', type=int)
    novo_status = request.form.get('ativo') == 'true'

    if not emp_reg:
        flash('Empresa não informada.', 'danger')
        return redirect(url_for('admin.listar_empresas'))

    empresa = Empresa.query.get(emp_reg)
    if not empresa:
        flash('Empresa não encontrada.', 'danger')
        return redirect(url_for('admin.listar_empresas'))

    # Evitar desativar a própria empresa do master (opcional, mas recomendado)
    if not novo_status and empresa.emp_cnpj == '10250216000169':  # CNPJ da OTICAS DINIZ sem pontuação
        flash('Não é permitido desativar a empresa master.', 'warning')
        return redirect(url_for('admin.listar_empresas'))

    empresa.emp_ativo = novo_status
    db.session.commit()
    status_msg = 'ativada' if novo_status else 'desativada'
    flash(f'✅ Empresa "{empresa.emp_razao_social}" {status_msg}!', 'success')
    return redirect(url_for('admin.listar_empresas'))

# =============== AMBIENTE ===============
@bp.route('/ambientes')
@login_required
def listar_ambientes():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    ambientes = Ambiente.query.all()
    return render_template('admin/ambientes.html', ambientes=ambientes)

# =============== CLIENTE ===============
@bp.route('/clientes')
@login_required
def listar_clientes():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    clientes = Cliente.query.filter_by(cli_ativo=True).all()
    return render_template('admin/clientes.html', clientes=clientes)

@bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
def novo_cliente():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    if request.method == 'POST':
        nome = request.form.get('cli_nome', '').strip().upper()
        cpf_cnpj = request.form.get('cli_cpf_cnpj', '').strip()

        if not nome or not cpf_cnpj:
            flash('Nome e CPF/CNPJ são obrigatórios.', 'danger')
            return render_template('admin/cliente_form.html', **request.form)

        # Limpar CPF/CNPJ
        documento = ''.join(filter(str.isdigit, cpf_cnpj))
        if len(documento) not in (11, 14):
            flash('CPF ou CNPJ inválido.', 'danger')
            return render_template('admin/cliente_form.html', **request.form)

        # Verificar duplicidade
        if Cliente.query.filter_by(cli_cpf_cnpj=documento).first():
            flash('CPF/CNPJ já cadastrado.', 'danger')
            return render_template('admin/cliente_form.html', **request.form)

        # Empresa atual
        empresa_id = current_user.us_empresa_id if hasattr(current_user, 'us_empresa_id') else 1

        novo = Cliente(
            cli_nome=nome,
            cli_cpf_cnpj=documento,
            cli_cep=request.form.get('cli_cep', '').strip(),
            cli_endereco=request.form.get('cli_endereco', '').strip().upper(),
            cli_bairro=request.form.get('cli_bairro', '').strip().upper(),
            cli_cidade=request.form.get('cli_cidade', '').strip().upper(),
            cli_uf=request.form.get('cli_uf', '').strip().upper(),
            cli_telefone=request.form.get('cli_telefone', '').strip(),
            cli_empresa_id=empresa_id,
            cli_ativo=True
        )
        db.session.add(novo)
        db.session.commit()
        flash(f'✅ Cliente "{nome}" cadastrado!', 'success')
        return redirect(url_for('admin.listar_clientes'))

    return render_template('admin/cliente_form.html')

@bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    cliente = Cliente.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form.get('cli_nome', '').strip().upper()
        cpf_cnpj = request.form.get('cli_cpf_cnpj', '').strip()

        if not nome or not cpf_cnpj:
            flash('Nome e CPF/CNPJ são obrigatórios.', 'danger')
            return render_template('admin/cliente_form.html', cliente=cliente, **request.form)

        documento = ''.join(filter(str.isdigit, cpf_cnpj))
        if len(documento) not in (11, 14):
            flash('CPF ou CNPJ inválido.', 'danger')
            return render_template('admin/cliente_form.html', cliente=cliente, **request.form)

        # Verificar duplicidade (exceto o próprio cliente)
        outro = Cliente.query.filter(
            Cliente.cli_cpf_cnpj == documento,
            Cliente.cli_reg != cliente.cli_reg
        ).first()
        if outro:
            flash('CPF/CNPJ já cadastrado.', 'danger')
            return render_template('admin/cliente_form.html', cliente=cliente, **request.form)

        # Atualizar campos
        cliente.cli_nome = nome
        cliente.cli_cpf_cnpj = documento
        cliente.cli_cep = request.form.get('cli_cep', '').strip()
        cliente.cli_endereco = request.form.get('cli_endereco', '').strip().upper()
        cliente.cli_bairro = request.form.get('cli_bairro', '').strip().upper()
        cliente.cli_cidade = request.form.get('cli_cidade', '').strip().upper()
        cliente.cli_uf = request.form.get('cli_uf', '').strip().upper()
        cliente.cli_telefone = request.form.get('cli_telefone', '').strip()

        db.session.commit()
        flash(f'✅ Cliente "{nome}" atualizado!', 'success')
        return redirect(url_for('admin.listar_clientes'))

    return render_template('admin/cliente_form.html', cliente=cliente)

@bp.route('/clientes/toggle-ativo', methods=['POST'])
@login_required
def toggle_cliente_ativo():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.listar_clientes'))

    cli_reg = request.form.get('cli_reg', type=int)
    novo_status = request.form.get('ativo') == 'true'

    if not cli_reg:
        flash('Cliente não informado.', 'danger')
        return redirect(url_for('admin.listar_clientes'))

    cliente = Cliente.query.get(cli_reg)
    if not cliente:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('admin.listar_clientes'))

    cliente.cli_ativo = novo_status
    db.session.commit()

    status_msg = 'ativado' if novo_status else 'desativado'
    flash(f'✅ Cliente "{cliente.cli_nome}" {status_msg}!', 'success')
    return redirect(url_for('admin.listar_clientes'))

# =============== FORNECEDOR ===============
@bp.route('/fornecedores')
@login_required
def listar_fornecedores():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    fornecedores = Fornecedor.query.filter_by(forn_ativo=True).all()
    return render_template('admin/fornecedores.html', fornecedores=fornecedores)

@bp.route('/fornecedores/novo', methods=['GET', 'POST'])
@login_required
def novo_fornecedor():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    if request.method == 'POST':
        # 👇 Usar EXATAMENTE os mesmos nomes do formulário e do modelo
        cnpj = request.form.get('forn_cnpj', '').strip()
        razao = request.form.get('forn_razao', '').strip()  # ← "forn_razao", não "forn_nome"
        fantasia = request.form.get('forn_fantasia', '').strip()

        if not razao or not cnpj:
            flash('Razão Social e CNPJ são obrigatórios.', 'danger')
            return render_template('admin/fornecedor_form.html', **request.form)

        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ deve ter 14 dígitos.', 'danger')
            return render_template('admin/fornecedor_form.html', **request.form)

        if Fornecedor.query.get(cnpj_limpo):  # como CNPJ é PK
            flash('CNPJ já cadastrado.', 'danger')
            return render_template('admin/fornecedor_form.html', **request.form)

        # Empresa
        empresa_id = current_user.us_empresa_id if hasattr(current_user, 'us_empresa_id') else 1

        # 👇 Criar com os campos EXATOS do modelo
        novo = Fornecedor(
            forn_cnpj=cnpj_limpo,
            forn_razao=razao,
            forn_fantasia=fantasia or razao,
            forn_representante=request.form.get('forn_representante', '').strip(),
            forn_tel_representante=request.form.get('forn_tel_representante', '').strip(),
            forn_cep=request.form.get('forn_cep', '').strip(),
            forn_endereco=request.form.get('forn_endereco', '').strip(),
            forn_bairro=request.form.get('forn_bairro', '').strip(),
            forn_cidade=request.form.get('forn_cidade', '').strip(),
            forn_uf=request.form.get('forn_uf', '').strip(),
            forn_telefone=request.form.get('forn_telefone', '').strip(),
            forn_email=request.form.get('forn_email', '').strip(),
            forn_empresa_id=empresa_id,
            forn_ativo=True
        )
        db.session.add(novo)
        db.session.commit()
        flash(f'✅ Fornecedor "{razao}" cadastrado!', 'success')
        return redirect(url_for('admin.listar_fornecedores'))

    return render_template('admin/fornecedor_form.html')

@bp.route('/fornecedores/editar/<cnpj>', methods=['GET', 'POST'])
@login_required
def editar_fornecedor(cnpj):
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    # Buscar fornecedor pelo CNPJ (PK)
    fornecedor = Fornecedor.query.get_or_404(cnpj)

    if request.method == 'POST':
        razao = request.form.get('forn_razao', '').strip()
        fantasia = request.form.get('forn_fantasia', '').strip()
        novo_cnpj = request.form.get('forn_cnpj', '').strip()

        if not razao or not novo_cnpj:
            flash('Razão Social e CNPJ são obrigatórios.', 'danger')
            return render_template('admin/fornecedor_form.html', fornecedor=fornecedor, **request.form)

        cnpj_limpo = ''.join(filter(str.isdigit, novo_cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ inválido.', 'danger')
            return render_template('admin/fornecedor_form.html', fornecedor=fornecedor, **request.form)

        # Verificar se CNPJ mudou e já existe
        if cnpj_limpo != fornecedor.forn_cnpj:
            if Fornecedor.query.get(cnpj_limpo):
                flash('CNPJ já cadastrado.', 'danger')
                return render_template('admin/fornecedor_form.html', fornecedor=fornecedor, **request.form)
            fornecedor.forn_cnpj = cnpj_limpo

        # Atualizar campos
        fornecedor.forn_razao = razao
        fornecedor.forn_fantasia = fantasia or razao
        fornecedor.forn_representante = request.form.get('forn_representante', '').strip()
        fornecedor.forn_tel_representante = request.form.get('forn_tel_representante', '').strip()
        fornecedor.forn_cep = request.form.get('forn_cep', '').strip()
        fornecedor.forn_endereco = request.form.get('forn_endereco', '').strip()
        fornecedor.forn_bairro = request.form.get('forn_bairro', '').strip()
        fornecedor.forn_cidade = request.form.get('forn_cidade', '').strip()
        fornecedor.forn_uf = request.form.get('forn_uf', '').strip()
        fornecedor.forn_telefone = request.form.get('forn_telefone', '').strip()
        fornecedor.forn_email = request.form.get('forn_email', '').strip()

        db.session.commit()
        flash(f'✅ Fornecedor "{razao}" atualizado!', 'success')
        return redirect(url_for('admin.listar_fornecedores'))

    return render_template('admin/fornecedor_form.html', fornecedor=fornecedor)

@bp.route('/fornecedores/toggle-ativo', methods=['POST'])
@login_required
def toggle_fornecedor_ativo():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.listar_fornecedores'))

    cnpj = request.form.get('forn_cnpj')
    novo_status = request.form.get('ativo') == 'true'

    if not cnpj:
        flash('Fornecedor não informado.', 'danger')
        return redirect(url_for('admin.listar_fornecedores'))

    fornecedor = Fornecedor.query.get(cnpj)
    if not fornecedor:
        flash('Fornecedor não encontrado.', 'danger')
        return redirect(url_for('admin.listar_fornecedores'))

    fornecedor.forn_ativo = novo_status
    db.session.commit()

    status_msg = 'ativado' if novo_status else 'desativado'
    flash(f'✅ Fornecedor "{fornecedor.forn_razao}" {status_msg}!', 'success')
    return redirect(url_for('admin.listar_fornecedores'))

# =============== PRODUTO ===============
@bp.route('/produtos')
@login_required
def listar_produtos():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    return render_template('admin/produtos.html',
                           produtos_armacao=Produto.query.filter_by(prod_tipo='armacao', prod_ativo=True).all(),
                           produtos_servico=Produto.query.filter_by(prod_tipo='servico', prod_ativo=True).all(),
                           aba_ativa=request.args.get('aba', 'armacao'))

@bp.route('/produtos/novo/<tipo>', methods=['GET', 'POST'])
@login_required
def novo_produto_tipo(tipo):
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    item_id = request.args.get('item_id')
    preco_sugerido = request.args.get('preco', type=float)
    fornecedor_cnpj = request.args.get('fornecedor')

    # 👇 Verifica se item já está associado
    if item_id:
        from ..models import ItemEntrada
        item = ItemEntrada.query.get(item_id)
        if item and item.produto_id:
            flash('Este item já está associado a um produto.', 'warning')
            return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))

    if tipo == 'lente':
        return redirect(url_for('admin.listar_lentes_genericas'))
    elif tipo not in ['armacao', 'servico']:
        flash('Tipo inválido.', 'danger')
        return redirect(url_for('admin.listar_produtos'))

    fornecedores = Fornecedor.query.filter_by(forn_ativo=True).all() if tipo == 'armacao' else []

    if request.method == 'POST':
        # Geração do código
        if tipo == 'armacao':
            codigo_barras = gerar_proximo_codigo('armacao')
        else:
            codigo_barras = gerar_proximo_codigo('servico')

        # Preço
        preco_custo_str = request.form.get('preco_custo', '').replace(',', '.')
        try:
            preco_custo = float(preco_custo_str) if preco_custo_str else 0.0
        except ValueError:
            flash('Preço inválido.', 'danger')
            return render_template(f'admin/produto_form_{tipo}.html',
                                  fornecedores=fornecedores,
                                  item_id=item_id,
                                  preco_sugerido=preco_sugerido,
                                  fornecedor_cnpj=fornecedor_cnpj)

        # Empresa
        empresa_nome = 'Cruz Dev Soft'
        empresa_id = 1
        if hasattr(current_user, 'empresa') and current_user.empresa:
            empresa_nome = current_user.empresa.nome
            empresa_id = current_user.us_empresa_id

        if tipo == 'armacao':
            tipo_aramacao = request.form.get('tipo_aramacao', '').strip()
            descricao_iniciais = request.form.get('descricao_iniciais', '').strip().upper()
            peca = request.form.get('peca', '').strip().upper()
            cor = request.form.get('cor', '').strip()
            tamanho = request.form.get('tamanho', '').strip()
            ponte = request.form.get('ponte', '').strip()

            if not all([tipo_aramacao, descricao_iniciais, peca, cor, tamanho, ponte]):
                flash('Todos os campos de armação são obrigatórios.', 'danger')
                return render_template('admin/produto_form_armacao.html',
                                      fornecedores=fornecedores,
                                      item_id=item_id,
                                      preco_sugerido=preco_sugerido,
                                      fornecedor_cnpj=fornecedor_cnpj)
            if tipo_aramacao not in {'AR', 'OC'}:
                flash('Tipo de armação inválido.', 'danger')
                return render_template('admin/produto_form_armacao.html',
                                      fornecedores=fornecedores,
                                      item_id=item_id,
                                      preco_sugerido=preco_sugerido,
                                      fornecedor_cnpj=fornecedor_cnpj)

            # 👇 Verificação COMPLETA (evita duplicação por cor/tamanho/ponte)
            fabricante_id = request.form.get('fabricante_id')
            produto_existente = Produto.query.filter_by(
                prod_peca=peca,
                prod_fabricante_id=fabricante_id,
                prod_cor=cor,
                prod_tamanho=tamanho,
                prod_ponte=ponte,
                prod_tipo='armacao'
            ).first()

            if produto_existente:
                flash(f'Armação "{peca}" já cadastrada com essas especificações.', 'info')
                if item_id:
                    item = ItemEntrada.query.get(item_id)
                    if item and not item.produto_id:
                        item.produto_id = produto_existente.prod_reg
                        db.session.commit()
                    return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))
                return redirect(url_for('admin.listar_produtos', aba='armacao'))

            nome_produto = f"{descricao_iniciais} {peca} {cor} {tamanho} {ponte}"
            novo = Produto(
                prod_codigo_barras=codigo_barras,
                prod_nome=nome_produto,
                prod_preco_custo=preco_custo,
                prod_tipo='armacao',
                prod_empresa=empresa_nome,
                prod_empresa_id=empresa_id,
                prod_fabricante_id=fabricante_id or None,
                prod_tipo_aramacao=tipo_aramacao,
                prod_descricao_iniciais=descricao_iniciais,
                prod_peca=peca,
                prod_cor=cor,
                prod_tamanho=tamanho,
                prod_ponte=ponte,
                prod_codigo_arma=peca,
                prod_ativo=True
            )

        else:  # serviço
            descricao_servico = request.form.get('descricao_servico', '').strip()
            if not descricao_servico:
                flash('Descrição do serviço é obrigatória.', 'danger')
                return render_template('admin/produto_form_servico.html',
                                      fornecedores=[],
                                      item_id=item_id,
                                      preco_sugerido=preco_sugerido,
                                      fornecedor_cnpj=fornecedor_cnpj)
            nome_produto = descricao_servico.upper()
            novo = Produto(
                prod_codigo_barras=codigo_barras,
                prod_nome=nome_produto,
                prod_preco_custo=preco_custo,
                prod_tipo='servico',
                prod_empresa=empresa_nome,
                prod_empresa_id=empresa_id,
                prod_descricao_servico=descricao_servico,
                prod_ativo=True
            )

        db.session.add(novo)
        db.session.flush()

        # Salvar foto
        if tipo == 'armacao' and peca:
            if 'imagem' in request.files:
                imagem = request.files['imagem']
                if imagem and imagem.filename != '':
                    nome_arquivo = secure_filename(f"{peca}.jpg")
                    caminho = os.path.join("static/fotos_armacoes", nome_arquivo)
                    os.makedirs("static/fotos_armacoes", exist_ok=True)
                    imagem.save(caminho)

        db.session.commit()
        flash(f'✅ {tipo.capitalize()} "{novo.prod_nome}" cadastrado!', 'success')

        # Associação com item da NF-e
        if item_id:
            item = ItemEntrada.query.get(item_id)
            if item and item.produto_id is None:
                item.produto_id = novo.prod_reg
                db.session.commit()
            return redirect(url_for('entradas.editar_entrada', entrada_id=item.entrada_id))

        return redirect(url_for('admin.listar_produtos', aba=tipo))

    return render_template(f'admin/produto_form_{tipo}.html',
                          fornecedores=fornecedores,
                          item_id=item_id,
                          preco_sugerido=preco_sugerido,
                          fornecedor_cnpj=fornecedor_cnpj)

@bp.route('/produtos/editar/<codigo_barras>', methods=['GET', 'POST'])
@login_required
def editar_produto(codigo_barras):
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    produto = Produto.query.filter_by(prod_codigo_barras=codigo_barras).first_or_404()
    tipo = produto.prod_tipo
    if tipo == 'lente':
        flash('Lentes são gerenciadas pelo sistema de grades.', 'warning')
        return redirect(url_for('admin.listar_lentes_genericas'))
    elif tipo not in ['armacao', 'servico']:
        flash('Tipo de produto não suportado.', 'danger')
        return redirect(url_for('admin.listar_produtos'))
    fornecedores = Fornecedor.query.filter_by(forn_ativo=True).all() if tipo == 'armacao' else []
    if request.method == 'POST':
        preco_custo_str = request.form.get('preco_custo', '').replace(',', '.')
        try:
            preco_custo = float(preco_custo_str) if preco_custo_str else 0.0
        except ValueError:
            flash('Preço inválido.', 'danger')
            return render_template(f'admin/produto_form_{tipo}.html', produto=produto, fornecedores=fornecedores)
        if tipo == 'armacao':
            tipo_aramacao = request.form.get('tipo_aramacao', '').strip()
            descricao_iniciais = request.form.get('descricao_iniciais', '').strip().upper()
            peca = request.form.get('peca', '').strip().upper()
            cor = request.form.get('cor', '').strip()
            tamanho = request.form.get('tamanho', '').strip()
            ponte = request.form.get('ponte', '').strip()
            if not all([tipo_aramacao, descricao_iniciais, peca, cor, tamanho, ponte]):
                flash('Todos os campos de armação são obrigatórios.', 'danger')
                return render_template('admin/produto_form_armacao.html', produto=produto, fornecedores=fornecedores)
            if tipo_aramacao not in {'AR', 'OC'}:
                flash('Tipo de armação inválido.', 'danger')
                return render_template('admin/produto_form_armacao.html', produto=produto, fornecedores=fornecedores)
            nome_produto = f"{descricao_iniciais} {peca} {cor} {tamanho} {ponte}"
            produto.prod_preco_custo = preco_custo
            produto.prod_tipo_aramacao = tipo_aramacao
            produto.prod_descricao_iniciais = descricao_iniciais
            produto.prod_peca = peca
            produto.prod_cor = cor
            produto.prod_tamanho = tamanho
            produto.prod_ponte = ponte
            produto.prod_nome = nome_produto
            produto.prod_fabricante_id = request.form.get('fabricante_id') or None
        else:  # servico
            descricao_servico = request.form.get('descricao_servico', '').strip()
            if not descricao_servico:
                flash('Descrição do serviço é obrigatória.', 'danger')
                return render_template('admin/produto_form_servico.html', produto=produto, fornecedores=[])
            nome_produto = descricao_servico.upper()
            produto.prod_preco_custo = preco_custo
            produto.prod_descricao_servico = descricao_servico
            produto.prod_nome = nome_produto
        db.session.commit()
        flash(f'✅ {tipo.capitalize()} "{produto.prod_nome}" atualizado!', 'success')
        return redirect(url_for('admin.listar_produtos', aba=tipo))
    return render_template(f'admin/produto_form_{tipo}.html', produto=produto, fornecedores=fornecedores)

# =============== LENTES GENÉRICAS ===============
@bp.route('/lentes-genericas')
@login_required
def listar_lentes_genericas():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    genericas = LenteGenerica.query.all()
    return render_template('admin/lente_generica_list.html', genericas=genericas)

@bp.route('/lentes-genericas/novo', methods=['GET', 'POST'])
@login_required
def nova_lente_generica():
    if not _tem_permissao():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    fornecedores = Fornecedor.query.filter_by(forn_ativo=True).all()
    if request.method == 'POST':
        try:
            esf_min = float(request.form['esf_min'].replace(',', '.'))
            esf_max = float(request.form['esf_max'].replace(',', '.'))
            cil_min = float(request.form['cil_min'].replace(',', '.'))
            cil_max = float(request.form['cil_max'].replace(',', '.'))
            add_min = float(request.form['add_min'].replace(',', '.'))
            add_max = float(request.form['add_max'].replace(',', '.'))
            preco_base = float(request.form['preco_base'].replace(',', '.'))
        except ValueError:
            flash('Valores numéricos inválidos.', 'danger')
            return render_template('admin/lente_generica_form.html', fornecedores=fornecedores)
        if esf_min > esf_max or cil_min < cil_max or add_min > add_max:
            flash('Faixa mínima não pode ser maior que máxima.', 'danger')
            return render_template('admin/lente_generica_form.html', fornecedores=fornecedores)
        codigo_base = gerar_proximo_codigo('lente')
        generica = LenteGenerica(
            codigo_base=codigo_base,
            descricao=request.form['descricao'].strip().upper(),
            tipo_lente=request.form['tipo_lente'],
            id_refracao=request.form['id_refracao'],
            fabricante_id=request.form.get('fabricante_id') or None,
            preco_base=preco_base,
            antirreflexo=request.form.get('antirreflexo', '').strip().upper() or None,
            escurecimento=request.form.get('escurecimento', '').strip().upper() or None,
            esf_min=esf_min,
            esf_max=esf_max,
            cil_min=cil_min,
            cil_max=cil_max,
            add_min=add_min,
            add_max=add_max,
            altura_fixa=request.form.get('altura_fixa') or None
        )
        db.session.add(generica)
        db.session.commit()
        try:
            combinacoes = gerar_combinacoes_lente(generica)
            os.makedirs('static/grades', exist_ok=True)
            grade_path = f"static/grades/{generica.codigo_base}.json.gz"
            with gzip.open(grade_path, 'wt', encoding='utf-8') as f:
                json.dump(combinacoes, f, ensure_ascii=False)
            flash(f'Lente genérica "{generica.descricao}" criada com {len(combinacoes)} combinações!', 'success')
        except Exception as e:
            flash(f'Erro ao gerar grade: {str(e)}', 'warning')
        return redirect(url_for('admin.listar_lentes_genericas'))
    return render_template('admin/lente_generica_form.html', fornecedores=fornecedores)

# =============== VENDEDOR ===============
@bp.route('/vendedores', methods=['GET', 'POST'])
@login_required
def listar_vendedores():
    if current_user.us_email not in ['cruz@devsoft', 'master@system']:
        if current_user.us_tipo != 'administrador':
            flash('Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('admin.home'))

    if request.method == 'POST':
        # Verificar se é uma edição (campo oculto vend_reg presente)
        vend_reg = request.form.get('vend_reg', type=int)
        
        vend_nome = request.form.get('vend_nome', '').strip().upper()
        vend_empresa = request.form.get('vend_empresa', '').strip().upper()

        if not vend_nome or not vend_empresa:
            flash('Nome e Empresa são obrigatórios.', 'warning')
        else:
            if vend_reg:
                # ⚙️ É uma EDIÇÃO
                vendedor = Vendedor.query.get(vend_reg)
                if vendedor:
                    vendedor.vend_nome = vend_nome
                    vendedor.vend_empresa = vend_empresa
                    db.session.commit()
                    flash(f'✅ Vendedor "{vend_nome}" atualizado!', 'success')
                else:
                    flash('Vendedor não encontrado.', 'danger')
            else:
                # ➕ É um NOVO cadastro
                ultimo = db.session.query(db.func.max(Vendedor.vend_reg)).scalar()
                proximo = (ultimo or 0) + 1
                codigo = f"{proximo:04d}"
                if Vendedor.query.filter_by(vend_codigo=codigo).first():
                    flash('Erro ao gerar código único. Tente novamente.', 'danger')
                else:
                    novo = Vendedor(vend_codigo=codigo, vend_nome=vend_nome, vend_empresa=vend_empresa)
                    db.session.add(novo)
                    db.session.commit()
                    flash(f'✅ Vendedor "{codigo}" cadastrado!', 'success')

    vendedores = Vendedor.query.all()
    return render_template('admin/vendedores.html', vendedores=vendedores)

@bp.route('/vendedores/editar/<int:id>', methods=['GET'])
@login_required
def editar_vendedor(id):
    if current_user.us_email not in ['cruz@devsoft', 'master@system']:
        if current_user.us_tipo != 'administrador':
            flash('Permissão insuficiente.', 'danger')
            return redirect(url_for('admin.home'))

    vendedor_edit = Vendedor.query.get_or_404(id)
    
    # Carregar todos os vendedores para a lista
    vendedores = Vendedor.query.all()
    
    # Passar o vendedor a ser editado para o template
    return render_template(
        'admin/vendedores.html',
        vendedores=vendedores,
        vendedor_edit=vendedor_edit  # ← dado do vendedor sendo editado
    )

@bp.route('/vendedores/toggle-ativo', methods=['POST'])
@login_required
def toggle_vendedor_ativo():
    if current_user.us_email not in ['cruz@devsoft', 'master@system']:
        if current_user.us_tipo != 'administrador':
            flash('Permissão insuficiente.', 'danger')
            return redirect(url_for('admin.listar_vendedores'))

    vend_reg = request.form.get('vend_reg', type=int)
    
    if not vend_reg:
        flash('Vendedor não informado.', 'danger')
        return redirect(url_for('admin.listar_vendedores'))

    vendedor = Vendedor.query.get(vend_reg)
    if not vendedor:
        flash('Vendedor não encontrado.', 'danger')
        return redirect(url_for('admin.listar_vendedores'))

    vendedor.vend_ativo = False  # seu formulário só tem "Desativar"
    db.session.commit()
    flash(f'✅ Vendedor "{vendedor.vend_nome}" desativado!', 'success')
    return redirect(url_for('admin.listar_vendedores'))

# =============== BANCOS ===============
@bp.route('/bancos')
@login_required
def listar_bancos():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))
    bancos = Banco.query.filter_by(ban_ativo=True).all()
    return render_template('admin/bancos.html', bancos=bancos)

@bp.route('/bancos/novo', methods=['GET', 'POST'])
@login_required
def novo_banco():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    if request.method == 'POST':
        codigo = request.form.get('ban_codigo', '').strip()
        nome = request.form.get('ban_nome', '').strip().upper()

        if not codigo or not nome:
            flash('Código e Nome do Banco são obrigatórios.', 'danger')
            return render_template('admin/banco_form.html', **request.form)

        if Banco.query.filter_by(ban_codigo=codigo).first():
            flash('Código do banco já cadastrado.', 'danger')
            return render_template('admin/banco_form.html', **request.form)

        empresa_id = current_user.us_empresa_id if hasattr(current_user, 'us_empresa_id') else 1

        novo = Banco(
            ban_codigo=codigo,
            ban_nome=nome,
            ban_empresa_id=empresa_id,
            ban_ativo=True
            # Campos extras (agência, conta, etc.) podem ser adicionados depois
        )
        db.session.add(novo)
        db.session.commit()
        flash(f'✅ Banco "{nome}" cadastrado!', 'success')
        return redirect(url_for('admin.listar_bancos'))

    return render_template('admin/banco_form.html')

@bp.route('/bancos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_banco(id):
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    banco = Banco.query.get_or_404(id)

    if request.method == 'POST':
        codigo = request.form.get('ban_codigo', '').strip()
        nome = request.form.get('ban_nome', '').strip().upper()

        if not codigo or not nome:
            flash('Código e Nome do Banco são obrigatórios.', 'danger')
            return render_template('admin/banco_form.html', banco=banco, **request.form)

        outro = Banco.query.filter(
            Banco.ban_codigo == codigo,
            Banco.ban_reg != banco.ban_reg
        ).first()
        if outro:
            flash('Código do banco já cadastrado.', 'danger')
            return render_template('admin/banco_form.html', banco=banco, **request.form)

        banco.ban_codigo = codigo
        banco.ban_nome = nome
        db.session.commit()
        flash(f'✅ Banco "{nome}" atualizado!', 'success')
        return redirect(url_for('admin.listar_bancos'))

    return render_template('admin/banco_form.html', banco=banco)

@bp.route('/bancos/toggle-ativo', methods=['POST'])
@login_required
def toggle_banco_ativo():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.listar_bancos'))

    ban_reg = request.form.get('ban_reg', type=int)
    novo_status = request.form.get('ativo') == 'true'

    if ban_reg:
        banco = Banco.query.get(ban_reg)
        if banco:
            banco.ban_ativo = novo_status
            db.session.commit()
            acao = 'ativado' if novo_status else 'desativado'
            flash(f'✅ Banco "{banco.ban_nome}" {acao}!', 'success')

    return redirect(url_for('admin.listar_bancos'))

# =============== TIPOS DE CARTÃO ===============
@bp.route('/tipos-cartao')
@login_required
def listar_tipos_cartao():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))
    tipos = TipoCartao.query.filter_by(tca_ativo=True).all()
    return render_template('admin/tipos_cartao.html', tipos=tipos)

@bp.route('/tipos-cartao/novo', methods=['GET', 'POST'])
@login_required
def novo_tipo_cartao():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    if request.method == 'POST':
        descricao = request.form.get('tca_descricao', '').strip().upper()
        tipo = request.form.get('tca_tipo', '')  # 'credito' ou 'debito'
        parcelas = request.form.get('tca_parcelas', '1')
        taxa_credito = request.form.get('tca_taxa_credito', '0').replace(',', '.')
        taxa_debito = request.form.get('tca_taxa_debito', '0').replace(',', '.')

        if not descricao or not tipo:
            flash('Descrição e Tipo são obrigatórios.', 'danger')
            return render_template('admin/tipo_cartao_form.html', **request.form)

        try:
            taxa_credito = float(taxa_credito) if taxa_credito else 0.0
            taxa_debito = float(taxa_debito) if taxa_debito else 0.0
            parcelas = int(parcelas) if tipo == 'credito' else 1
        except ValueError:
            flash('Valores numéricos inválidos.', 'danger')
            return render_template('admin/tipo_cartao_form.html', **request.form)

        empresa_id = current_user.us_empresa_id if hasattr(current_user, 'us_empresa_id') else 1

        novo = TipoCartao(
            tca_descricao=descricao,
            tca_tipo=tipo,
            tca_parcelas=parcelas,
            tca_taxa_credito=taxa_credito,
            tca_taxa_debito=taxa_debito,
            tca_empresa_id=empresa_id,
            tca_ativo=True
        )
        db.session.add(novo)
        db.session.commit()
        flash(f'✅ Tipo de cartão "{descricao}" cadastrado!', 'success')
        return redirect(url_for('admin.listar_tipos_cartao'))

    return render_template('admin/tipo_cartao_form.html')

@bp.route('/tipos-cartao/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_tipo_cartao(id):
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))

    tipo_obj = TipoCartao.query.get_or_404(id)

    if request.method == 'POST':
        descricao = request.form.get('tca_descricao', '').strip().upper()
        tipo = request.form.get('tca_tipo', '')
        parcelas = request.form.get('tca_parcelas', '1')
        taxa_credito = request.form.get('tca_taxa_credito', '0').replace(',', '.')
        taxa_debito = request.form.get('tca_taxa_debito', '0').replace(',', '.')

        if not descricao or not tipo:
            flash('Descrição e Tipo são obrigatórios.', 'danger')
            return render_template('admin/tipo_cartao_form.html', tipo=tipo_obj, **request.form)

        try:
            taxa_credito = float(taxa_credito) if taxa_credito else 0.0
            taxa_debito = float(taxa_debito) if taxa_debito else 0.0
            parcelas = int(parcelas) if tipo == 'credito' else 1
        except ValueError:
            flash('Valores numéricos inválidos.', 'danger')
            return render_template('admin/tipo_cartao_form.html', tipo=tipo_obj, **request.form)

        tipo_obj.tca_descricao = descricao
        tipo_obj.tca_tipo = tipo
        tipo_obj.tca_parcelas = parcelas
        tipo_obj.tca_taxa_credito = taxa_credito
        tipo_obj.tca_taxa_debito = taxa_debito
        db.session.commit()
        flash(f'✅ Tipo de cartão "{descricao}" atualizado!', 'success')
        return redirect(url_for('admin.listar_tipos_cartao'))

    return render_template('admin/tipo_cartao_form.html', tipo=tipo_obj)

@bp.route('/tipos-cartao/toggle-ativo', methods=['POST'])
@login_required
def toggle_tipo_cartao_ativo():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.listar_tipos_cartao'))

    tca_reg = request.form.get('tca_reg', type=int)
    novo_status = request.form.get('ativo') == 'true'

    if tca_reg:
        tipo = TipoCartao.query.get(tca_reg)
        if tipo:
            tipo.tca_ativo = novo_status
            db.session.commit()
            acao = 'ativado' if novo_status else 'desativado'
            flash(f'✅ Tipo de cartão "{tipo.tca_descricao}" {acao}!', 'success')

    return redirect(url_for('admin.listar_tipos_cartao'))

# =============== TIPOS DE CARNÊ ===============
@bp.route('/tipos-carne')
@login_required
def listar_tipos_carne():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))
    tipos = TipoCarne.query.filter_by(tcn_ativo=True).all()
    return render_template('admin/tipos_carne.html', tipos=tipos)

# =============== OPERAÇÕES DE CONCILIAÇÃO ===============
@bp.route('/operacoes-conciliacao')
@login_required
def listar_operacoes_conciliacao():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))
    operacoes = OperacaoConciliacao.query.filter_by(opc_ativo=True).all()
    return render_template('admin/operacoes_conciliacao.html', operacoes=operacoes)

# =============== FERIADOS ===============
@bp.route('/feriados')
@login_required
def listar_feriados():
    if current_user.us_email not in ['cruz@devsoft', 'master@system'] and current_user.us_tipo != 'administrador':
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('admin.home'))
    feriados = Feriado.query.filter_by(fer_ativo=True).all()
    return render_template('admin/feriados.html', feriados=feriados)

# ===============PESQUISAS PARA CAIXA ===============
@bp.route('/pesquisa-armacoes')
@login_required
def pesquisa_armacoes():
    """Tela de pesquisa de armações (para uso no caixa)"""
    return render_template('admin/pesquisa_armacoes.html')

@bp.route('/pesquisa-lentes')
@login_required
def pesquisa_lentes():
    """Tela de pesquisa de lentes (para uso no caixa)"""
    return render_template('admin/pesquisa_lentes.html')

@bp.route('/pesquisa-produtos')
@login_required
def pesquisa_produtos():
    """Tela de pesquisa de produtos (para uso no caixa)"""
    return render_template('admin/pesquisa_produtos.html')

# Convênios
@bp.route('/convenios')
@login_required
def lista_convenios():
    convenios = Convenio.query.all()
    return render_template('admin/convenios.html', convenios=convenios)

@bp.route('/convenios/novo', methods=['GET', 'POST'])
@login_required
def novo_convenio():
    if request.method == 'POST':
        conv = Convenio(
            conv_nome=request.form['nome'],
            conv_ativo='ativo' in request.form
        )
        db.session.add(conv)
        db.session.commit()
        flash('Convênio salvo com sucesso!', 'success')
        return redirect(url_for('admin.lista_convenios'))
    return render_template('admin/convenio_form.html')

# Laboratórios
@bp.route('/laboratorios')
@login_required
def lista_laboratorios():
    labs = Laboratorio.query.all()
    return render_template('admin/laboratorios.html', laboratorios=labs)

# Médicos
@bp.route('/medicos')
@login_required
def lista_medicos():
    medicos = Medico.query.all()
    return render_template('admin/medicos.html', medicos=medicos)

@bp.route('/ambientes/toggle-ativo', methods=['POST'])
@login_required
def toggle_ambiente_ativo():
    """Ativa/desativa um ambiente"""
    amb_id = request.form.get('amb_id')
    ambiente = Ambiente.query.get(amb_id)
    if ambiente:
        ambiente.amb_ativo = not ambiente.amb_ativo
        db.session.commit()
        flash(f"Ambiente '{ambiente.amb_nome}' {'ativado' if ambiente.amb_ativo else 'desativado'} com sucesso!", "success")
    else:
        flash("Ambiente não encontrado.", "danger")
    
    return redirect(url_for('admin.listar_ambientes'))