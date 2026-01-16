import os
from dotenv import load_dotenv

# Carrega variáveis do .env (obrigatório por causa do crypto.py)
load_dotenv()

from app import create_app
from app.models import Ambiente
from app.extensions import db

app = create_app()

with app.app_context():
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
            print(f"✅ Ambiente '{nome}' adicionado.")
        else:
            print(f"⚠️ Ambiente '{nome}' já existe.")

    db.session.commit()
    print("✅ Todos os ambientes foram verificados/cadastrados.")