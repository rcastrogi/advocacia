from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Verificar se a coluna existe
        result = db.session.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'saved_petitions'
            AND column_name = 'petition_model_id'
        """)
        )

        if result.fetchone():
            print("SUCCESS: Coluna petition_model_id existe")
        else:
            print("ERROR: Coluna petition_model_id não existe")

            # Tentar adicionar a coluna
            print("Tentando adicionar a coluna...")
            db.session.execute(
                text("""
                ALTER TABLE saved_petitions
                ADD COLUMN petition_model_id INTEGER REFERENCES petition_models(id)
            """)
            )
            db.session.commit()
            print("SUCCESS: Coluna adicionada")

    except Exception as e:
        print(f"ERROR: {e}")
