import os
import sqlite3

def fix_database():
    db_path = 'instance/database.db'
    
    # Conecta ao banco de dados
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Adiciona a coluna template_project_id se ela não existir
        cursor.execute("""
        ALTER TABLE settings 
        ADD COLUMN template_project_id INTEGER 
        REFERENCES project(id);
        """)
        print("Coluna template_project_id adicionada com sucesso!")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("A coluna template_project_id já existe")
        else:
            print(f"Erro ao adicionar coluna: {e}")
    
    # Lista todas as tabelas e suas colunas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTabelas encontradas:")
    for table in tables:
        print(f"\nTabela: {table[0]}")
        cursor.execute(f"PRAGMA table_info({table[0]});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    fix_database()
