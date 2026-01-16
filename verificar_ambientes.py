import os
from dotenv import load_dotenv

# Carrega o .env
load_dotenv()

# Configuração manual do banco (sem depender do Flask)
import sqlite3

# Caminho do banco
DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'devsoft.db')

def main():
    print(f"🔍 Acessando banco: {DB_PATH}")
    
    # Conectar ao banco
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Verificar estrutura da tabela
    try:
        cursor.execute("PRAGMA table_info(tb_ambiente);")
        columns = cursor.fetchall()
        print("\n📋 Estrutura da tabela tb_ambiente:")
        for col in columns:
            print(f"  {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")
    except Exception as e:
        print(f"❌ Erro ao ler estrutura: {e}")
        return
    
    # Ver dados atuais
    try:
        cursor.execute("SELECT amb_id, amb_nome, amb_ativo FROM tb_ambiente;")
        rows = cursor.fetchall()
        print(f"\n📊 Dados atuais ({len(rows)} registros):")
        for row in rows:
            print(f"  ID: {row[0]} | Nome: {row[1]} | Ativo: {row[2]}")
    except Exception as e:
        print(f"❌ Erro ao ler dados: {e}")
        return
    
    # Corrigir registros com amb_ativo = NULL ou 0
    try:
        cursor.execute("UPDATE tb_ambiente SET amb_ativo = 1 WHERE amb_ativo IS NULL OR amb_ativo = 0;")
        updated = cursor.rowcount
        if updated > 0:
            conn.commit()
            print(f"\n✅ {updated} ambiente(s) corrigido(s)!")
        else:
            print("\n✅ Todos os ambientes já estão ativos.")
    except Exception as e:
        print(f"❌ Erro ao atualizar: {e}")
        return
    
    conn.close()
    print("\n✨ Operação concluída!")

if __name__ == "__main__":
    main()