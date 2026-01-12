import os
import json
import gzip
from decimal import Decimal
from flask import current_app

def gerar_valores(min_val, max_val, step):
    """Gera lista de valores com passo fixo (ex: -6.00, -5.75, ..., 6.00)"""
    valores = []
    current = Decimal(str(min_val))
    step = Decimal(str(step))
    max_val = Decimal(str(max_val))
    while current <= max_val:
        valores.append(f"{current:.2f}")
        current += step
    return valores


def gerar_combinacoes_lente(generica):
    """Gera todas as combinações válidas de uma lente genérica."""
    esf_vals = gerar_valores(generica.esf_min, generica.esf_max, generica.esf_step)
    cil_vals = gerar_valores(generica.cil_max, generica.cil_min, generica.cil_step)  # cil_max é negativo!
    add_vals = gerar_valores(generica.add_min, generica.add_max, generica.add_step)

    combinacoes = []
    sequencia = 1
    for esf in esf_vals:
        for cil in cil_vals:
            for add in add_vals:
                codigo_barras = f"{generica.codigo_base}{sequencia:04d}"
                nome = f"LG {generica.descricao} {generica.tipo_lente} {generica.id_refracao} {esf} {cil} {add}".upper()
                if generica.antirreflexo:
                    nome += f" {generica.antirreflexo.upper()}"
                if generica.escurecimento:
                    nome += f" {generica.escurecimento.upper()}"

                combinacoes.append({
                    'codigo': codigo_barras,
                    'nome': nome,
                    'esf': esf,
                    'cil': cil,
                    'add': add,
                    'altura': generica.altura_fixa or "18",
                    'preco': float(generica.preco_base)
                })
                sequencia += 1
    return combinacoes


def salvar_grade_compactada(generica, combinacoes):
    """Salva as combinações em arquivo JSON compactado."""
    # Diretório relativo ao projeto (não ao módulo)
    base_dir = current_app.root_path
    grades_dir = os.path.join(base_dir, 'static', 'grades')
    os.makedirs(grades_dir, exist_ok=True)

    grade_path = os.path.join(grades_dir, f"{generica.codigo_base}.json.gz")
    with gzip.open(grade_path, 'wt', encoding='utf-8') as f:
        json.dump(combinacoes, f, ensure_ascii=False)


def buscar_combinacao_na_grade(codigo_base, esf, cil, add):
    """Busca uma combinação específica na grade compactada."""
    base_dir = current_app.root_path
    grade_path = os.path.join(base_dir, 'static', 'grades', f"{codigo_base}.json.gz")
    
    if not os.path.exists(grade_path):
        return None

    try:
        with gzip.open(grade_path, 'rt', encoding='utf-8') as f:
            combinacoes = json.load(f)

        esf_busca = f"{float(esf):.2f}"
        cil_busca = f"{float(cil):.2f}"
        add_busca = f"{float(add):.2f}"

        for item in combinacoes:
            if item['esf'] == esf_busca and item['cil'] == cil_busca and item['add'] == add_busca:
                return item
    except Exception:
        return None
    return None