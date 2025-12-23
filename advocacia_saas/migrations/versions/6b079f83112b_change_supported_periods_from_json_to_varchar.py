"""Change supported_periods from JSON to VARCHAR

Revision ID: 6b079f83112b
Revises: add_period_discounts
Create Date: 2025-12-23 09:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6b079f83112b"
down_revision = "add_period_discounts"
branch_labels = None
depends_on = None


def upgrade():
    # Change supported_periods column from JSON to VARCHAR(10)
    # First, we need to convert existing JSON data to string
    op.execute("""
        ALTER TABLE billing_plans
        ALTER COLUMN supported_periods TYPE VARCHAR(10)
        USING CASE
            WHEN json_typeof(supported_periods) = 'array' AND json_array_length(supported_periods) > 0
            THEN supported_periods->>0
            ELSE '1m'
        END
    """)


def downgrade():
    # Change supported_periods column back from VARCHAR to JSON
    op.execute("""
        ALTER TABLE billing_plans
        ALTER COLUMN supported_periods TYPE JSON
        USING json_build_array(supported_periods)
    """)
