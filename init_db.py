import os
from app import app, db

def init_database():
    # Remove o banco de dados existente
    db_path = os.path.join('instance', 'weconqui.db')
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
        
        # Cria as configurações iniciais
        from app import Settings
        settings = Settings()
        db.session.add(settings)
        db.session.commit()
        print("Configurações iniciais criadas")

if __name__ == '__main__':
    init_database()
