import os
from dotenv import load_dotenv  # ← adicionado

# Carrega as variáveis do .env na raiz do projeto
load_dotenv()  # ← adicionado (deve ser a primeira coisa!)

from app import create_app
from app.extensions import db
import app.models  # registra todos os modelos
from werkzeug.security import generate_password_hash

app = create_app()

# Flag global para garantir inicialização única
_banco_inicializado = False

def init_db_once():
    global _banco_inicializado
    if _banco_inicializado:
        return

    with app.app_context():
        try:
            from app.models import Usuario
            Usuario.query.first()  # Testa se o banco existe
            print("✅ Banco já inicializado.")
        except Exception:
            print("⚠️ Inicializando banco de dados...")
            db.create_all()

            from app.models import Ambiente, Usuario

            ambientes_necessarios = [
                ('administrador', 'Ambiente administrativo'),
                ('entradas', 'Módulo de Entradas'),
                ('saidas', 'Módulo de Saídas'),
                ('financeiro', 'Módulo Financeiro'),
                ('caixa', 'Caixa / PDV'),
                ('monitor_producao', 'Monitor de Produção')
            ]

            for nome, descricao in ambientes_necessarios:
                if not Ambiente.query.filter_by(amb_nome=nome).first():
                    ambiente = Ambiente(
                        amb_nome=nome,
                        amb_ativo=True,
                        amb_descricao=descricao
                    )
                    db.session.add(ambiente)

            if not Usuario.query.filter_by(us_email='cruz@devsoft').first():
                master = Usuario(
                    us_cad='Programador',
                    us_email='cruz@devsoft',
                    us_senha=generate_password_hash('DevsoftSistem'),
                    us_ativo=True,
                    us_forcar_troca_senha=False,
                    loja_id='01'
                )
                db.session.add(master)

            db.session.commit()
            print("✅ Banco inicializado com sucesso!")
        
        _banco_inicializado = True

@app.before_request
def ensure_db_initialized():
    global _banco_inicializado
    if not _banco_inicializado:
        init_db_once()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)