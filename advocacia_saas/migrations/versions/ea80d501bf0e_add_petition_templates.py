"""add_petition_templates

Revision ID: ea80d501bf0e
Revises: 8fd19d58ed3c
Create Date: 2025-11-23 01:16:22.944795

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ea80d501bf0e"
down_revision = "8fd19d58ed3c"
branch_labels = None
depends_on = None


def upgrade():
    # Garantir idempotência em ambientes onde create_all já criou a tabela
    op.execute("DROP TABLE IF EXISTS petition_templates")
    op.create_table(
        "petition_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "is_global", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("petition_type_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["petition_type_id"], ["petition_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade():
    op.drop_table("petition_templates")
