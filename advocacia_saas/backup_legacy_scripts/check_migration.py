from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    print("=== STATUS ATUAL ===")
    try:
        # Verificar via SQL
        result = db.session.execute(text("SELECT COUNT(*) FROM petition_models"))
        models_count = result.fetchone()[0]
        print(f"PetitionModel: {models_count} registros")

        result2 = db.session.execute(
            text("SELECT COUNT(*) FROM petition_model_sections")
        )
        sections_count = result2.fetchone()[0]
        print(f"PetitionModelSection: {sections_count} registros")

        # Mostrar alguns exemplos
        if models_count > 0:
            result3 = db.session.execute(
                text("""
                SELECT pm.name, pt.name as type_name, COUNT(pms.id) as sections_count
                FROM petition_models pm
                JOIN petition_types pt ON pm.petition_type_id = pt.id
                LEFT JOIN petition_model_sections pms ON pm.id = pms.petition_model_id
                GROUP BY pm.id, pm.name, pt.name
                LIMIT 3
            """)
            )
            print("\n=== EXEMPLOS DE MODELOS ===")
            for row in result3:
                print(f"{row[0]}: {row[2]} seções, Tipo: {row[1]}")

    except Exception as e:
        print(f"Erro ao consultar tabelas: {e}")

    print("\n=== TIPOS DINÂMICOS ===")
    from app.models import PetitionType

    dynamic_count = PetitionType.query.filter_by(use_dynamic_form=True).count()
    print(f"Tipos dinâmicos restantes: {dynamic_count}")
