import requests

# Cache simples em memória
_cep_cache = {}

def buscar_cep(cep):
    if not cep:
        return None
    cep_limpo = ''.join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        return None

    if cep_limpo in _cep_cache:
        return _cep_cache[cep_limpo]

    try:
        # ⚠️ Corrija o espaço na URL!
        response = requests.get(f'https://viacep.com.br/ws/{cep_limpo}/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'erro' not in data:
                resultado = {
                    'endereco': data.get('logradouro', '') or '',
                    'bairro': data.get('bairro', '') or '',
                    'cidade': data.get('localidade', '') or '',
                    'uf': data.get('uf', '') or ''
                }
                _cep_cache[cep_limpo] = resultado
                return resultado
    except Exception:
        pass
    return None