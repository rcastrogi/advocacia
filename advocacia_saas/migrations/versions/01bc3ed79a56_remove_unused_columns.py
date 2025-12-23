"""Remove unused columns usage_rate and period_discounts

Revision ID: 01bc3ed79a56
Revises: 6b079f83112b
Create Date: 2025-12-23 09:35:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "01bc3ed79a56"
down_revision = "6b079f83112b"
branch_labels = None
depends_on = None


def upgrade():
    # Remove usage_rate column
    op.drop_column("billing_plans", "usage_rate")

    # Remove period_discounts column
    op.drop_column("billing_plans", "period_discounts")


def downgrade():
    # Add back usage_rate column
    op.add_column(
        "billing_plans", sa.Column("usage_rate", sa.Numeric(10, 2), nullable=True)
    )

    # Add back period_discounts column
    op.add_column(
        "billing_plans", sa.Column("period_discounts", sa.JSON(), nullable=True)
    )
