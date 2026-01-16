import os
from cryptography.fernet import Fernet

# Carrega a chave do ambiente (.env)
CHAVE_CRIPT = os.getenv('CHAVE_CRIPT_CERTIFICADO')

if not CHAVE_CRIPT:
    raise RuntimeError("❌ Variável 'CHAVE_CRIPT_CERTIFICADO' não definida no arquivo .env")

try:
    fernet = Fernet(CHAVE_CRIPT.encode())
except Exception as e:
    raise RuntimeError(
        "❌ Chave de criptografia inválida. Certifique-se de que 'CHAVE_CRIPT_CERTIFICADO' "
        "é uma string base64 válida (ex: gerada por Fernet.generate_key())."
    ) from e


def criptografar_senha(senha: str) -> str:
    """Criptografa uma senha em texto puro. Retorna string vazia se a senha for None ou vazia."""
    if not senha:
        return ""
    return fernet.encrypt(senha.encode()).decode()


def descriptografar_senha(senha_cript: str) -> str:
    """Descriptografa uma senha criptografada. Retorna string vazia se a entrada for None ou vazia."""
    if not senha_cript:
        return ""
    return fernet.decrypt(senha_cript.encode()).decode()