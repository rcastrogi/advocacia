from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    print("Checking process-related tables...")

    # Usar inspector para verificar tabelas
    inspector = inspect(db.engine)

    # Verificar tabelas específicas
    tables_to_check = ["processes", "process_notifications", "user", "saved_petitions"]
    for table in tables_to_check:
        exists = table in inspector.get_table_names()
        print(f"{table} exists: {exists}")

    # Listar todas as tabelas
    tables = inspector.get_table_names()
    print(f"\nTotal tables in database: {len(tables)}")
    print("Process-related tables:")
    process_tables = [t for t in tables if "process" in t.lower()]
    for table in process_tables:
        print(f"  - {table}")
