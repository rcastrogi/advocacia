"""
Script para criar as tabelas de seções dinâmicas usando SQLAlchemy do Flask.
"""
from app import create_app, db

app = create_app()

print("=" * 70)
print("🔧 CRIANDO TABELAS DE SEÇÕES DINÂMICAS")
print("=" * 70)

with app.app_context():
    conn = db.engine.raw_connection()
    cur = conn.cursor()
    
    # Verificar se as tabelas já existem
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name IN ('petition_sections', 'petition_type_sections')
    """)
    existing = [row[0] for row in cur.fetchall()]
    
    if 'petition_sections' in existing:
        print("⚠️ Tabela petition_sections já existe")
    else:
        print("📦 Criando tabela petition_sections...")
        cur.execute("""
            CREATE TABLE petition_sections (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                slug VARCHAR(100) UNIQUE NOT NULL,
                description VARCHAR(255),
                icon VARCHAR(50) DEFAULT 'fa-file-alt',
                color VARCHAR(20) DEFAULT 'primary',
                "order" INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                fields_schema JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        print("✅ Tabela petition_sections criada!")
    
    if 'petition_type_sections' in existing:
        print("⚠️ Tabela petition_type_sections já existe")
    else:
        print("📦 Criando tabela petition_type_sections...")
        cur.execute("""
            CREATE TABLE petition_type_sections (
                id SERIAL PRIMARY KEY,
                petition_type_id INTEGER NOT NULL REFERENCES petition_types(id),
                section_id INTEGER NOT NULL REFERENCES petition_sections(id),
                "order" INTEGER DEFAULT 0,
                is_required BOOLEAN DEFAULT FALSE,
                is_expanded BOOLEAN DEFAULT TRUE,
                field_overrides JSONB DEFAULT '{}'::jsonb
            )
        """)
        conn.commit()
        print("✅ Tabela petition_type_sections criada!")
    
    # Adicionar colunas novas ao petition_types se não existirem
    print("\n📦 Verificando colunas adicionais em petition_types...")
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'petition_types' AND column_name = 'icon'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE petition_types ADD COLUMN icon VARCHAR(50) DEFAULT 'fa-file-alt'")
        conn.commit()
        print("  ✅ Coluna 'icon' adicionada")
    else:
        print("  ⚠️ Coluna 'icon' já existe")
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'petition_types' AND column_name = 'use_dynamic_form'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE petition_types ADD COLUMN use_dynamic_form BOOLEAN DEFAULT FALSE")
        conn.commit()
        print("  ✅ Coluna 'use_dynamic_form' adicionada")
    else:
        print("  ⚠️ Coluna 'use_dynamic_form' já existe")
    
    cur.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ TABELAS CRIADAS COM SUCESSO!")
    print("=" * 70)
    print("\n💡 Próximo passo: Execute setup_petition_sections.py para popular as seções")
