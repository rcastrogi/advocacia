"""add client_lawyers association table

Revision ID: add_client_lawyers
Revises: 1a2b3c4d5e6f
Create Date: 2025-12-19 00:00:00.000000

"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_client_lawyers"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela de associação client_lawyers
    op.create_table(
        "client_lawyers",
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("lawyer_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column("specialty", sa.String(length=100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=True, default=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["client.id"],
        ),
        sa.ForeignKeyConstraint(
            ["lawyer_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("client_id", "lawyer_id"),
    )

    # Migrar dados existentes: adicionar o lawyer_id atual de cada cliente na tabela de associação
    op.execute("""
        INSERT INTO client_lawyers (client_id, lawyer_id, created_at, is_primary)
        SELECT id, lawyer_id, created_at, TRUE
        FROM client
        WHERE lawyer_id IS NOT NULL
    """)


def downgrade():
    # Remover tabela de associação
    op.drop_table("client_lawyers")
