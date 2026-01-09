"""Script para criar tabelas diretamente no banco"""

from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    sql1 = """
    CREATE TABLE IF NOT EXISTS template_examples (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        template_content TEXT NOT NULL,
        petition_type_id INTEGER REFERENCES petition_types(id),
        tags VARCHAR(500),
        quality_score FLOAT DEFAULT 5.0,
        usage_count INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        source VARCHAR(50) DEFAULT 'manual',
        original_model_id INTEGER REFERENCES petition_models(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER REFERENCES "user"(id)
    );
    """
    
    # SQL para atualizar coluna caso tabela já exista
    sql1_alter = """
    ALTER TABLE template_examples 
    ALTER COLUMN quality_score TYPE FLOAT USING quality_score::float;
    """

    sql2 = """
    CREATE TABLE IF NOT EXISTS ai_generation_feedback (
        id SERIAL PRIMARY KEY,
        petition_model_id INTEGER REFERENCES petition_models(id),
        generated_template TEXT NOT NULL,
        rating INTEGER NOT NULL,
        feedback_type VARCHAR(20),
        feedback_text TEXT,
        action_taken VARCHAR(30),
        edited_template TEXT,
        prompt_used TEXT,
        sections_used JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER REFERENCES "user"(id)
    );
    """

    try:
        db.session.execute(text(sql1))
        print("✅ Tabela template_examples criada")
    except Exception as e:
        print(f"❌ template_examples: {e}")

    # Tentar alterar tipo da coluna quality_score (caso já exista como INTEGER)
    try:
        db.session.execute(text(sql1_alter))
        print("✅ Coluna quality_score alterada para FLOAT")
    except Exception as e:
        print(f"ℹ️ quality_score já é FLOAT ou tabela não existe: {e}")

    try:
        db.session.execute(text(sql2))
        print("✅ Tabela ai_generation_feedback criada")
    except Exception as e:
        print(f"❌ ai_generation_feedback: {e}")

    db.session.commit()
    print("✅ Tabelas criadas com sucesso!")
