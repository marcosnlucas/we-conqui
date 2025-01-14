import sqlite3
from app import app, db

def add_template_project():
    with app.app_context():
        # Adiciona a coluna template_project_id ao modelo Settings
        class Settings(db.Model):
            __tablename__ = 'settings'
            id = db.Column(db.Integer, primary_key=True)
            logo_path = db.Column(db.String(255))
            favicon_path = db.Column(db.String(255))
            template_project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
            created_at = db.Column(db.DateTime)
            updated_at = db.Column(db.DateTime)
            template_project = db.relationship('Project', foreign_keys=[template_project_id])
        
        # Conecta ao banco de dados
        conn = sqlite3.connect('instance/database.db')
        cursor = conn.cursor()
        
        try:
            # Adiciona a coluna template_project_id
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
    add_template_project()
