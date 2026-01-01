"""Add table_preferences for per-user table settings

Revision ID: 20260101_000001
Revises: 7605f8df8a9f
Create Date: 2026-01-01 00:00:01.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260101_000001"
down_revision = "7605f8df8a9f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "table_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("view_key", sa.String(length=200), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_table_preferences_user_view",
        "table_preferences",
        ["user_id", "view_key"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_user_view", "table_preferences", ["user_id", "view_key"]
    )


def downgrade():
    op.drop_constraint("uq_user_view", "table_preferences", type_="unique")
    op.drop_index("ix_table_preferences_user_view", table_name="table_preferences")
    op.drop_table("table_preferences")
