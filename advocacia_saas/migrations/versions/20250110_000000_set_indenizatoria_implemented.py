"""Set is_implemented for Indenizatoria petition type.

Revision ID: 20250110_000000
Revises: 20260108_000000
Create Date: 2025-01-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250110_000000'
down_revision = '20260108_000000'
branch_labels = None
depends_on = None


def upgrade():
    # Set is_implemented=true for the Indenizatoria petition type
    op.execute("""
        UPDATE petition_types
        SET is_implemented = true
        WHERE slug = 'modelo-acao-civil-indenizatoria'
    """)


def downgrade():
    # Revert is_implemented=false for the Indenizatoria petition type
    op.execute("""
        UPDATE petition_types
        SET is_implemented = false
        WHERE slug = 'modelo-acao-civil-indenizatoria'
    """)
