from flask import Flask
from .extensions import db, login_manager
from .utils.filters import format_currency
from dotenv import load_dotenv

# Carrega variáveis do .env ANTES de importar outros módulos
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.secret_key = 'dev-secret-universal'
    app.jinja_env.filters['format_currency'] = format_currency

    import os
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'devsoft.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    # 👇 VERIFICAÇÃO GLOBAL DE AMBIENTE
    from flask import request, redirect, url_for, flash
    from flask_login import current_user

    @app.before_request
    def verificar_ambiente():
        if not request.endpoint:
            return
        if request.endpoint in ['auth.login', 'auth.logout', 'static']:
            return
        if not current_user.is_authenticated:
            return

        # Master tem acesso total
        if hasattr(current_user, 'us_email') and current_user.us_email in {'cruz@devsoft', 'master@system'}:
            return

        # Usuários comuns: verificar ambientes_permitidos
        if not hasattr(current_user, 'ambientes_permitidos') or len(current_user.ambientes_permitidos) == 0:
            flash("Usuário não tem ambiente associado.", "danger")
            return redirect(url_for('auth.logout'))

    # 👇 REGISTRO DE BLUEPRINTS
    from .routes import auth
    from .routes.admin import bp as admin_bp
    from .routes.entradas import bp as entradas_bp
    from .routes.saidas import bp as saidas_bp
    from .routes.financeiro import bp as financeiro_bp
    from .routes.caixa import bp as caixa_bp

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(entradas_bp, url_prefix='/entradas')
    app.register_blueprint(saidas_bp, url_prefix='/saidas')
    app.register_blueprint(financeiro_bp, url_prefix='/financeiro')
    app.register_blueprint(caixa_bp, url_prefix='/caixa')

    # 👇 CONTEXT PROCESSOR PARA INJETAR AMBIENTES NO TEMPLATE
    @app.context_processor
    def inject_ambientes():
        from flask_login import current_user
        ambientes_permitidos = []
        try:
            if current_user.is_authenticated:
                from .models import Ambiente

                # Super admin: vê todos os ambientes ativos
                if hasattr(current_user, 'us_email') and current_user.us_email in {'cruz@devsoft', 'master@system'}:
                    ambientes_permitidos = Ambiente.query.filter_by(amb_ativo=True).all()
                else:
                    # Usuário comum: usa ambientes_permitidos do próprio usuário
                    if hasattr(current_user, 'ambientes_permitidos'):
                        ambientes_permitidos = current_user.ambientes_permitidos
                    else:
                        ambientes_permitidos = []
        except Exception:
            ambientes_permitidos = []
        return dict(ambientes_permitidos=ambientes_permitidos)

    return app