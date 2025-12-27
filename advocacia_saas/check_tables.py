from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        result = db.session.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'petition_models')"
            )
        )
        exists = result.fetchone()[0]
        print("Tabela petition_models existe:", exists)

        if exists:
            result2 = db.session.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'petition_model_sections')"
                )
            )
            exists2 = result2.fetchone()[0]
            print("Tabela petition_model_sections existe:", exists2)
        else:
            print("Criando tabelas...")
            # Criar tabelas
            create_table_sql = text("""
            CREATE TABLE petition_models (
                id SERIAL PRIMARY KEY,
                name VARCHAR(180) NOT NULL,
                slug VARCHAR(80) UNIQUE NOT NULL,
                description TEXT,
                petition_type_id INTEGER REFERENCES petition_types(id) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                use_dynamic_form BOOLEAN DEFAULT TRUE,
                default_template_id INTEGER REFERENCES petition_templates(id),
                created_by INTEGER REFERENCES "user"(id),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            create_sections_sql = text("""
            CREATE TABLE petition_model_sections (
                id SERIAL PRIMARY KEY,
                petition_model_id INTEGER REFERENCES petition_models(id) NOT NULL,
                section_id INTEGER REFERENCES petition_sections(id) NOT NULL,
                "order" INTEGER DEFAULT 0,
                is_required BOOLEAN DEFAULT FALSE,
                is_expanded BOOLEAN DEFAULT TRUE,
                field_overrides JSON DEFAULT '{}',
                UNIQUE(petition_model_id, section_id)
            );
            """)

            db.session.execute(create_table_sql)
            db.session.execute(create_sections_sql)
            db.session.commit()
            print("Tabelas criadas com sucesso!")

    except Exception as e:
        print(f"Erro: {e}")
        db.session.rollback()
