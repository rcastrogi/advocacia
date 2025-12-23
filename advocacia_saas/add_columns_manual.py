#!/usr/bin/env python3
"""Script para adicionar colunas manualmente ao banco Render"""

from app import create_app
from app.models import db
from sqlalchemy import text


def add_columns():
    """Adiciona as colunas de períodos flexíveis e desconto"""
    app = create_app()
    app.app_context().push()

    try:
        # Adicionar coluna supported_periods
        db.session.execute(
            text("""
            ALTER TABLE billing_plans
            ADD COLUMN IF NOT EXISTS supported_periods JSON
            DEFAULT '["1m", "3m", "6m", "1y", "2y", "3y"]'
        """)
        )

        # Adicionar coluna discount_percentage
        db.session.execute(
            text("""
            ALTER TABLE billing_plans
            ADD COLUMN IF NOT EXISTS discount_percentage NUMERIC(5,2)
            DEFAULT 0.00
        """)
        )

        db.session.commit()
        print("✅ Colunas adicionadas com sucesso!")

    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        db.session.rollback()


if __name__ == "__main__":
    add_columns()
