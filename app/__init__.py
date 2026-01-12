from flask import Flask
from .extensions import db, login_manager
from .utils.filters import format_currency

def create_app():
    app = Flask(__name__, template_folder='../templates')

    app.secret_key = 'dev-secret-universal'

    app.jinja_env.filters['format_currency'] = format_currency

    # Configuração do banco de dados
    import os
    os.makedirs(app.instance_path, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'devsoft.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    # Importar e registrar blueprints
    from .routes import auth
    from .routes.admin import bp as admin_bp
    from .routes.entradas import bp as entradas_bp
    from .routes.saidas import bp as saidas_bp
    from .routes.financeiro import bp as financeiro_bp
    from .routes.caixa import bp as caixa_bp 
      

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(entradas_bp, url_prefix='/entradas')
    app.register_blueprint(saidas_bp, url_prefix='/saidas')  
    app.register_blueprint(financeiro_bp, url_prefix='/financeiro')  
    app.register_blueprint(caixa_bp, url_prefix='/caixa')        

    # Context Processor para injetar ambientes no template
    @app.context_processor
    def inject_ambientes():
        from flask_login import current_user
        ambientes_permitidos = []
        try:
            if current_user.is_authenticated:
                # Importação tardia para evitar circular import / mapper errors
                from .models import Ambiente

                # Super admin (programador master) vê todos os ambientes ativos
                if hasattr(current_user, 'us_email') and current_user.us_email in ['cruz@devsoft', 'master@system']:
                    ambientes_permitidos = Ambiente.query.filter_by(amb_ativo=True).all()
                else:
                    # Demais usuários: usam os ambientes da empresa vinculada
                    if hasattr(current_user, 'empresa') and current_user.empresa:
                        ambientes_permitidos = current_user.empresa.ambientes_permitidos
                    elif hasattr(current_user, 'ambiente') and current_user.ambiente:
                        ambientes_permitidos = [current_user.ambiente]
                    else:
                        ambientes_permitidos = []
        except Exception:
            ambientes_permitidos = []
        return dict(ambientes_permitidos=ambientes_permitidos)

    return app