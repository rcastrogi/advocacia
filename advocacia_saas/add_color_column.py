"""Script para adicionar coluna color à tabela petition_types."""
from app import create_app, db

app = create_app()

with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    
    # Verificar se color já existe
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'petition_types' AND column_name = 'color'
    """)
    
    if not cur.fetchone():
        print("Adicionando coluna 'color'...")
        cur.execute("ALTER TABLE petition_types ADD COLUMN color VARCHAR(20) DEFAULT 'primary'")
        conn.commit()
        print("Coluna 'color' adicionada!")
    else:
        print("Coluna 'color' já existe.")
    
    cur.close()
    conn.close()
    print("Concluído!")
