"""Update credit_packages columns

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2024-12-17 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "g2b3c4d5e6f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona colunas faltantes na tabela credit_packages
    op.add_column(
        "credit_packages",
        sa.Column("bonus_credits", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "credit_packages", sa.Column("original_price", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        "credit_packages",
        sa.Column("currency", sa.String(3), nullable=True, server_default="BRL"),
    )
    op.add_column(
        "credit_packages", sa.Column("updated_at", sa.DateTime(), nullable=True)
    )

    # Remove colunas antigas se existirem
    try:
        op.drop_column("credit_packages", "price_per_credit")
    except:
        pass

    try:
        op.drop_column("credit_packages", "discount_percentage")
    except:
        pass


def downgrade():
    op.drop_column("credit_packages", "bonus_credits")
    op.drop_column("credit_packages", "original_price")
    op.drop_column("credit_packages", "currency")
    op.drop_column("credit_packages", "updated_at")
