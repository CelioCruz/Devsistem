from ..extensions import db
from sqlalchemy import func
from ..models import OrdemServico

# Função para gerar próximo CV (global)
def gerar_proximo_cv():
    max_cv = db.session.query(func.max(OrdemServico.cv_numero)).scalar()
    return (max_cv or 0) + 1

# Função para gerar próximo OS (por loja)
def gerar_proximo_os(loja_id: str) -> str:
    # Validação
    if not loja_id.isdigit() or not (1 <= int(loja_id) <= 99):
        raise ValueError("loja_id deve ser de 01 a 99")
    loja_id = loja_id.zfill(2)  # '1' vira '01'
    
    # Maior OS dessa loja
    max_os = db.session.query(
        func.max(OrdemServico.os_numero)
    ).filter(
        OrdemServico.os_numero.like(f"{loja_id}%")
    ).scalar()
    
    if max_os:
        sequencial = int(max_os[2:]) + 1
    else:
        sequencial = 1  # Começa em 00001 → valor 1
    
    return f"{loja_id}{sequencial:05d}"  # ex: '0100001'