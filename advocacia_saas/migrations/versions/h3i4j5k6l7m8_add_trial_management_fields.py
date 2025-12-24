"""Add trial management fields to User model

Revision ID: h3i4j5k6l7m8
Revises: g2b3c4d5e6f7
Create Date: 2025-12-23 21:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "h3i4j5k6l7m8"
down_revision = "g2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("trial_start_date", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("trial_days", sa.Integer(), nullable=True))
    op.add_column("user", sa.Column("trial_active", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "trial_start_date")
    op.drop_column("user", "trial_days")
    op.drop_column("user", "trial_active")
