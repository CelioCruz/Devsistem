from app import create_app
from app.extensions import db
import os

# ✅ Importação única que registra TODOS os modelos
import app.models

from werkzeug.security import generate_password_hash

app = create_app()

def init_db():
    """Cria tabelas e dados iniciais — execute UMA VEZ via console"""
    with app.app_context():
        db.create_all()

        from app.models import Ambiente, Usuario

        # --- Criação de Ambientes ---
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

if __name__ == '__main__':
    # ⚠️ NUNCA use debug=True em produção!
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)