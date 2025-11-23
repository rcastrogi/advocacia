"""add is_implemented to petition types

Revision ID: c7f57f083480
Revises: 5d4c0b8d1bb6
Create Date: 2024-07-18 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7f57f083480"
down_revision = "5d4c0b8d1bb6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "petition_types",
        sa.Column(
            "is_implemented",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.execute(
        """
        UPDATE petition_types
        SET is_implemented = TRUE
        WHERE slug IN ('peticao-inicial-civel', 'peticao-familia-divorcio')
        """
    )


def downgrade():
    op.drop_column("petition_types", "is_implemented")
