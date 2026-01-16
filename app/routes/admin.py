import os
import json
import gzip
import decimal
from datetime import datetime
from io import BytesIO
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, jsonify, send_file
)
from flask_login import login_required, current_user

from app.extensions import db
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
from app.models.convenio import Convenio
from app.models.laboratorio import Laboratorio
from app.models.medico import Medico

from app.utils.cep import buscar_cep
from app.utils.codigos import gerar_proximo_codigo
from app.utils.lentes import gerar_combinacoes_lente
from app.utils.crypto import criptografar_senha

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
    
    ambientes = Ambiente.query.filter_by(amb_ativo=True).all()
    empresas = Empresa.query.filter_by(emp_ativo=True).all()
    
    if request.method == 'POST':
        if 'excluir_usuario' in request.form:
            us_reg = request.form.get('us_reg', type=int)
            usuario = Usuario.query.get(us_reg)
            if usuario and usuario.us_email != 'cruz@devsoft':
                db.session.delete(usuario)
                db.session.commit()
                flash(f'✅ Usuário "{usuario.us_cad}" excluído!', 'success')
            elif usuario:
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
                        usuario.ambientes_permitidos = [] if is_admin else Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
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
                        novo.ambientes_permitidos = [] if is_admin else Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
                        db.session.add(novo)
                        db.session.commit()
                        flash('Usuário criado com sucesso!', 'success')
                        return redirect(url_for('admin.listar_usuarios'))
        
        usuarios = Usuario.query.all()
        return render_template('admin/usuarios.html', usuarios=usuarios, ambientes=ambientes, empresas=empresas)
    
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios, ambientes=ambientes, empresas=empresas)

@bp.route('/usuarios/toggle-ativo', methods=['POST'])
@login_required
def toggle_usuario_ativo():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    
    us_reg = request.form.get('us_reg')
    usuario = Usuario.query.get(us_reg)
    
    if usuario and usuario.us_email != 'cruz@devsoft':
        usuario.us_ativo = request.form.get('ativo') == 'true'
        db.session.commit()
        flash(f'Usuário {"ativado" if usuario.us_ativo else "desativado"}!', 'success')
    elif usuario:
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
    return render_template('admin/empresas_lista.html', empresas=empresas, now=datetime.now())

@bp.route('/empresas/nova', methods=['GET', 'POST'])
@login_required
def nova_empresa():
    if not _tem_permissao_master():
        flash('Somente o master pode criar empresas.', 'danger')
        return redirect(url_for('admin.listar_empresas'))
    
    todos_ambientes = Ambiente.query.filter_by(amb_ativo=True).all()
    
    if request.method == 'POST':
        razao_social = request.form.get('emp_razao_social', '').strip()
        nome_fantasia = request.form.get('emp_nome_fantasia', '').strip()
        cnpj = request.form.get('emp_cnpj', '').strip()
        
        if not razao_social or not cnpj:
            flash('Razão Social e CNPJ são obrigatórios.', 'danger')
            return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes, **request.form)
        
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ inválido.', 'danger')
            return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes, **request.form)
        
        if Empresa.query.filter_by(emp_cnpj=cnpj_limpo).first():
            flash('CNPJ já cadastrado.', 'danger')
            return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes, **request.form)

        # Processar certificado
        cert_data = None
        cert_file = request.files.get('emp_certificado_arquivo')
        if cert_file and cert_file.filename:
            filename = secure_filename(cert_file.filename)
            if not filename.lower().endswith(('.pfx', '.p12')):
                flash('Apenas arquivos .pfx ou .p12 são permitidos.', 'danger')
                return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes, **request.form)
            cert_data = cert_file.read()

        # Processar licença
        licenca_tipo = request.form.get('emp_licenca_tipo', 'permanente')
        licenca_data_fim = None
        if licenca_tipo == 'temporaria':
            data_str = request.form.get('emp_licenca_data_fim')
            if data_str:
                try:
                    licenca_data_fim = datetime.strptime(data_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de fim da licença inválida.', 'danger')
                    return render_template('admin/empresa_form.html', todos_ambientes=todos_ambientes, **request.form)

        senha_cript = criptografar_senha(request.form.get('emp_certificado_senha', ''))

        # Criar empresa
        nova_empresa_obj = Empresa(
            emp_razao_social=razao_social,
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
            emp_tipo=request.form.get('emp_tipo'),
            emp_certificado_a1=cert_data,
            emp_senha_certificado=senha_cript,
            emp_licenca_tipo=licenca_tipo,
            emp_licenca_data_fim=licenca_data_fim,
            emp_licenca_desativar_tempo=bool(request.form.get('emp_licenca_desativar_tempo')),
            emp_ativo=True
        )
        
        db.session.add(nova_empresa_obj)
        
        ambiente_ids = request.form.getlist('ambientes[]')
        if ambiente_ids:
            ambiente_ids = [int(aid) for aid in ambiente_ids if aid.isdigit()]
            ambientes_selecionados = Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
            nova_empresa_obj.ambientes_permitidos = ambientes_selecionados
        
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
            return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes, **request.form)
        
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if len(cnpj_limpo) != 14:
            flash('CNPJ inválido.', 'danger')
            return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes, **request.form)
        
        if Empresa.query.filter(Empresa.emp_cnpj == cnpj_limpo, Empresa.emp_reg != empresa.emp_reg).first():
            flash('CNPJ já cadastrado em outra empresa.', 'danger')
            return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes, **request.form)

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
        empresa.emp_tipo = request.form.get('emp_tipo')

        # Atualizar ambientes
        ambiente_ids = request.form.getlist('ambientes[]')
        if ambiente_ids:
            ambiente_ids = [int(aid) for aid in ambiente_ids if aid.isdigit()]
            empresa.ambientes_permitidos = Ambiente.query.filter(Ambiente.amb_id.in_(ambiente_ids)).all()
        else:
            empresa.ambientes_permitidos = []

        # Certificado
        cert_file = request.files.get('emp_certificado_arquivo')
        if cert_file and cert_file.filename:
            filename = secure_filename(cert_file.filename)
            if not filename.lower().endswith(('.pfx', '.p12')):
                flash('Apenas arquivos .pfx ou .p12 são permitidos.', 'danger')
                return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes, **request.form)
            empresa.emp_certificado_a1 = cert_file.read()

        empresa.emp_senha_certificado = criptografar_senha(request.form.get('emp_certificado_senha', ''))

        # Licença
        licenca_tipo = request.form.get('emp_licenca_tipo', 'permanente')
        empresa.emp_licenca_tipo = licenca_tipo
        if licenca_tipo == 'temporaria':
            data_str = request.form.get('emp_licenca_data_fim')
            if data_str:
                try:
                    empresa.emp_licenca_data_fim = datetime.strptime(data_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de fim da licença inválida.', 'danger')
                    return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes, **request.form)
            else:
                empresa.emp_licenca_data_fim = None
        else:
            empresa.emp_licenca_data_fim = None

        empresa.emp_licenca_desativar_tempo = bool(request.form.get('emp_licenca_desativar_tempo'))

        db.session.commit()
        flash(f'✅ Empresa "{empresa.emp_razao_social}" atualizada!', 'success')
        return redirect(url_for('admin.listar_empresas'))

    return render_template('admin/empresa_form.html', empresa=empresa, todos_ambientes=todos_ambientes)

@bp.route('/empresas/<int:id>/download-certificado')
@login_required
def download_certificado(id):
    if not _tem_permissao_master():
        flash('Acesso negado.', 'danger')
        return redirect(url_for('admin.listar_empresas'))
    
    empresa = Empresa.query.get_or_404(id)
    if not empresa.emp_certificado_a1:
        flash('Nenhum certificado cadastrado.', 'warning')
        return redirect(url_for('admin.editar_empresa', id=id))
    
    return send_file(
        BytesIO(empresa.emp_certificado_a1),
        mimetype='application/x-pkcs12',
        as_attachment=True,
        download_name=f'certificado_{empresa.emp_cnpj}.pfx'
    )

# =============== AMBIENTE ===============
@bp.route('/ambientes', methods=['GET', 'POST'])
@login_required
def listar_ambientes():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.home'))
    
    if request.method == 'POST':
        amb_nome = request.form.get('amb_nome', '').strip()
        amb_descricao = request.form.get('amb_descricao', '').strip()
        
        if not amb_nome:
            flash('Nome do ambiente é obrigatório.', 'danger')
        elif Ambiente.query.filter_by(amb_nome=amb_nome).first():
            flash('Este ambiente já existe.', 'danger')
        else:
            novo_ambiente = Ambiente(
                amb_nome=amb_nome,
                amb_descricao=amb_descricao if amb_descricao else None,
                amb_ativo=True
            )
            db.session.add(novo_ambiente)
            db.session.commit()
            flash(f"✅ Ambiente '{amb_nome}' criado com sucesso!", 'success')
            return redirect(url_for('admin.listar_ambientes'))
    
    ambientes = Ambiente.query.all()
    return render_template('admin/ambientes.html', ambientes=ambientes)

@bp.route('/ambientes/toggle-ativo', methods=['POST'])
@login_required
def toggle_ambiente_ativo():
    if not _tem_permissao_master():
        flash('Permissão insuficiente.', 'danger')
        return redirect(url_for('admin.listar_ambientes'))
    
    amb_id = request.form.get('amb_id')
    ambiente = Ambiente.query.get(amb_id)
    
    if ambiente:
        ambiente.amb_ativo = not ambiente.amb_ativo
        db.session.commit()
        flash(f"Ambiente '{ambiente.amb_nome}' {'ativado' if ambiente.amb_ativo else 'desativado'} com sucesso!", "success")
    else:
        flash("Ambiente não encontrado.", "danger")
    
    return redirect(url_for('admin.listar_ambientes'))