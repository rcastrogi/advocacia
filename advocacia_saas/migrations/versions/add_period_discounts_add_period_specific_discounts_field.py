"""Add period-specific discounts field

Revision ID: add_period_discounts
Revises: 996cf696b786
Create Date: 2025-12-23 09:21:43.690401

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_period_discounts"
down_revision = "996cf696b786"
branch_labels = None
depends_on = None


def upgrade():
    # Add period_discounts column to billing_plans table
    op.add_column(
        "billing_plans",
        sa.Column(
            "period_discounts",
            sa.JSON(),
            nullable=True,
            default={
                "1m": 0.0,
                "3m": 5.0,
                "6m": 7.0,
                "1y": 9.0,
                "2y": 13.0,
                "3y": 20.0,
            },
        ),
    )


def downgrade():
    # Remove period_discounts column from billing_plans table
    op.drop_column("billing_plans", "period_discounts")
