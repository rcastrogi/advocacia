"""add user_id to client

Revision ID: add_user_id_to_client
Revises: add_client_lawyers
Create Date: 2025-12-19 11:56:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_user_id_to_client"
down_revision = "add_client_lawyers"
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna user_id à tabela client
    op.add_column("client", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_client_user_id", "client", "user", ["user_id"], ["id"])


def downgrade():
    # Remover coluna user_id
    op.drop_constraint("fk_client_user_id", "client", type_="foreignkey")
    op.drop_column("client", "user_id")
