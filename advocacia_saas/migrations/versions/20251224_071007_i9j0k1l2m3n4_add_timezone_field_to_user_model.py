"""Add timezone field to User model

Revision ID: i9j0k1l2m3n4
Revises: h3i4j5k6l7m8
Create Date: 2025-12-24 07:10:07.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "i9j0k1l2m3n4"
down_revision = "h3i4j5k6l7m8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "timezone", sa.String(length=50), nullable=True, default="America/Sao_Paulo"
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "timezone")
