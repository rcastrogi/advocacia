"""add fee contract templates

Revision ID: fee_contract_templates_20260127
Revises: deadline_sync_20260119
Create Date: 2026-01-27
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fee_contract_templates_20260127"
down_revision = "deadline_sync_20260119"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fee_contract_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_fee_contract_templates_user_id",
        "fee_contract_templates",
        ["user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_fee_contract_templates_user_id", table_name="fee_contract_templates"
    )
    op.drop_table("fee_contract_templates")
