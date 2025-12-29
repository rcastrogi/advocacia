"""
Migração para adicionar modelos de andamentos, custos e anexos de processos
"""

from app import create_app, db
from app.models import ProcessAttachment, ProcessCost, ProcessMovement


def run_migration():
    """Executa a migração para criar as novas tabelas"""
    app = create_app()

    with app.app_context():
        print("Criando tabelas para andamentos, custos e anexos de processos...")

        try:
            # Criar tabelas
            ProcessMovement.__table__.create(db.engine, checkfirst=True)
            ProcessCost.__table__.create(db.engine, checkfirst=True)
            ProcessAttachment.__table__.create(db.engine, checkfirst=True)

            print("✅ Tabelas criadas com sucesso!")
            print("- process_movements")
            print("- process_costs")
            print("- process_attachments")

        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            return False

    return True


if __name__ == "__main__":
    run_migration()

if __name__ == "__main__":
    run_migration()
