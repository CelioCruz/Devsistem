from sqlalchemy import text
from ..extensions import db  # ← IMPORTANTE: importe db

def gerar_proximo_codigo(tipo):
    if tipo == 'armacao':
        result = db.session.execute(
            text("SELECT MAX(prod_codigo_barras) FROM tb_produto WHERE prod_codigo_barras LIKE '1%' AND prod_tipo = 'armacao'")
        ).scalar()
        base = 1000000
    elif tipo == 'lente':
        result = db.session.execute(
            text("SELECT MAX(codigo_base) FROM tb_lente_generica WHERE codigo_base LIKE '0%'")
        ).scalar()
        base = 0000000
    elif tipo == 'servico':
        result = db.session.execute(
            text("SELECT MAX(prod_codigo_barras) FROM tb_produto WHERE prod_codigo_barras LIKE '2%' AND prod_tipo = 'servico'")
        ).scalar()
        base = 2000000  
    else:
        raise ValueError("Tipo inválido")

    if result:
        try:
            ultimo_num = int(result)
            novo_num = ultimo_num + 1
        except (ValueError, TypeError):
            novo_num = base + 1
    else:
        novo_num = base + 1

    return f"{novo_num:07d}"