#!/usr/bin/env python3
"""Script para adicionar campos de política de cancelamento à tabela subscriptions"""

from app import create_app
from app.models import db
from sqlalchemy import text


def add_cancellation_fields():
    """Adiciona os campos de política de cancelamento"""
    app = create_app()
    app.app_context().push()

    try:
        # Adicionar campos de política de reembolso
        db.session.execute(
            text("""
            ALTER TABLE subscriptions
            ADD COLUMN IF NOT EXISTS refund_policy VARCHAR(20)
            DEFAULT 'no_refund'
        """)
        )

        db.session.execute(
            text("""
            ALTER TABLE subscriptions
            ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(10,2)
        """)
        )

        db.session.execute(
            text("""
            ALTER TABLE subscriptions
            ADD COLUMN IF NOT EXISTS refund_processed_at TIMESTAMP
        """)
        )

        db.session.commit()
        print("✅ Campos de política de cancelamento adicionados com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao adicionar campos: {e}")
        db.session.rollback()


if __name__ == "__main__":
    add_cancellation_fields()
