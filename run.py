from app import create_app
from app.extensions import db
import os

# ✅ Importação única que registra TODOS os modelos
import app.models

from werkzeug.security import generate_password_hash

app = create_app()

def init_db_once():
    """Inicializa o banco SOMENTE se ainda não existir"""
    with app.app_context():
        try:
            # Verifica se a tabela 'usuario' existe
            from app.models import Usuario
            Usuario.query.first()  # Isso falha se o banco não existir
            print("✅ Banco já inicializado.")
        except Exception as e:
            print(f"⚠️ Banco não encontrado. Inicializando... {e}")
            # Cria todas as tabelas
            db.create_all()

            # --- Criação de Ambientes ---
            from app.models import Ambiente
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

            # --- Criação do Usuário Master ---
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
            print("✅ Banco de dados inicializado com sucesso!")

# ⚠️ Executa na primeira requisição (funciona no Render)
@app.before_first_request
def initialize():
    init_db_once()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)