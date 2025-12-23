"""Add flexible billing periods and discount fields to BillingPlan

Revision ID: 7a6c7aa40f2c
Revises: a6567181c018
Create Date: 2025-12-23 07:25:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a6c7aa40f2c"
down_revision = "a6567181c018"
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to billing_plans table
    op.add_column(
        "billing_plans",
        sa.Column(
            "supported_periods",
            sa.JSON(),
            nullable=True,
            default=["1m", "3m", "6m", "1y", "2y", "3y"],
        ),
    )
    op.add_column(
        "billing_plans",
        sa.Column(
            "discount_percentage",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            default=0.00,
        ),
    )


def downgrade():
    # Remove the new columns
    op.drop_column("billing_plans", "discount_percentage")
    op.drop_column("billing_plans", "supported_periods")
