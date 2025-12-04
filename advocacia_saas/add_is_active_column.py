"""Script para adicionar colunas faltantes."""
from app import create_app, db

app = create_app()

with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    
    # Verificar e adicionar is_active
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'petition_types' AND column_name = 'is_active'
    """)
    
    if not cur.fetchone():
        print("Adicionando coluna 'is_active'...")
        cur.execute("ALTER TABLE petition_types ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
        conn.commit()
        print("Coluna 'is_active' adicionada!")
    else:
        print("Coluna 'is_active' já existe.")
    
    cur.close()
    conn.close()
    print("Concluído!")
