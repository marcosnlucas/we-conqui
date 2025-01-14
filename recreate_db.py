import os
import sqlite3
from app import app, db

def recreate_database():
    # Remove o banco de dados existente
    db_path = 'instance/database.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Banco de dados antigo removido: {db_path}")

    # Cria o diretório instance se não existir
    if not os.path.exists('instance'):
        os.makedirs('instance')
        print("Diretório instance criado")

    # Cria as tabelas usando SQLAlchemy
    with app.app_context():
        db.create_all()
        print("Tabelas criadas com SQLAlchemy")

        # Verifica a estrutura das tabelas
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lista todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nTabelas encontradas:")
        for table in tables:
            print(f"\nTabela: {table[0]}")
            cursor.execute(f"PRAGMA table_info({table[0]});")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        
        # Cria as configurações iniciais
        from app import Settings
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        print("\nConfigurações iniciais criadas")

if __name__ == '__main__':
    recreate_database()
