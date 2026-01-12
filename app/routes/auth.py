from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from ..models import *
import os

bp = Blueprint('auth', __name__)  

@bp.route('/')  
def index():
    return redirect(url_for('auth.login'))  

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        senha_digitada = request.form['senha']
        SENHA_MESTRA = os.environ.get('SENHA_MESTRA', 'DevsoftSistem')

        # Verifica se é o programador master
        if username == "cruz@devsoft" and senha_digitada == SENHA_MESTRA:
            class ProgramadorMaster:
                us_reg = -1  # ✅ ID virtual, apenas para identificação
                us_cad = "Programador"
                us_email = "cruz@devsoft"
                us_tipo = "super_admin"
                us_ativo = True
                us_empresa_id = None
                def get_id(self):
                    return "-1"
                def is_authenticated(self):
                    return True
                def is_active(self):
                    return True
                def is_anonymous(self):
                    return False
            usuario = ProgramadorMaster()
            autenticado = True
        else:
            # Verifica usuário comum (admin, vendedor, etc.)
            usuario = Usuario.query.filter_by(us_email=username).first()
            if usuario and usuario.us_ativo and check_password_hash(usuario.us_senha, senha_digitada):
                autenticado = True
            elif usuario and not usuario.us_ativo:
                flash('Usuário inativo.', 'danger')
            else:
                flash('Usuário ou senha inválidos.', 'danger')
                return render_template('login.html')

        if autenticado:
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')

            # Redirecionamento inteligente
            if getattr(usuario, 'us_tipo', None) == 'super_admin':
                return redirect(url_for('admin.home'))  # Super admin vai para home
            else:
                # Usuário comum vai para seu ambiente
                if hasattr(usuario, 'us_ambiente') and usuario.us_ambiente:
                    return redirect(url_for('admin.ver_ambiente', amb_id=usuario.us_ambiente.amb_id))
                else:
                    flash('Usuário não tem ambiente associado.', 'warning')
                    return redirect(url_for('auth.logout'))

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))