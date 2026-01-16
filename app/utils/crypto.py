import os
from cryptography.fernet import Fernet

# Carrega a chave do ambiente (.env ou variável de ambiente)
CHAVE_CRIPT = os.getenv('CHAVE_CRIPT_CERTIFICADO')

# Se não houver chave, gera uma padrão para não quebrar o startup
if not CHAVE_CRIPT:
    # Gera uma chave padrão para desenvolvimento/testes
    print("⚠️  AVISO: Variável 'CHAVE_CRIPT_CERTIFICADO' não definida. Usando chave padrão.")
    CHAVE_CRIPT = Fernet.generate_key().decode()

try:
    fernet = Fernet(CHAVE_CRIPT.encode())
except Exception as e:
    print("❌ Erro: Chave de criptografia inválida. Usando chave gerada automaticamente.")
    CHAVE_CRIPT = Fernet.generate_key().decode()
    fernet = Fernet(CHAVE_CRIPT.encode())


def criptografar_senha(senha: str) -> str:
    """Criptografa uma senha em texto puro. Retorna string vazia se a senha for None ou vazia."""
    if not senha:
        return ""
    try:
        return fernet.encrypt(senha.encode()).decode()
    except Exception as e:
        print(f"Erro ao criptografar: {e}")
        return ""


def descriptografar_senha(senha_cript: str) -> str:
    """Descriptografa uma senha criptografada. Retorna string vazia se a entrada for None ou vazia."""
    if not senha_cript:
        return ""
    try:
        return fernet.decrypt(senha_cript.encode()).decode()
    except Exception as e:
        print(f"Erro ao descriptografar: {e}")
        return ""