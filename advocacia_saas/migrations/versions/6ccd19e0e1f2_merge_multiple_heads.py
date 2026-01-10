"""Merge multiple heads

Revision ID: 6ccd19e0e1f2
Revises: 0e5042995e0f, 20251227_194700, 20260101_000001, 8fd19d58ed3c, j4k5l6m7n8o9
Create Date: 2026-01-10 10:50:59.221298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ccd19e0e1f2'
down_revision = ('0e5042995e0f', '20251227_194700', '20260101_000001', '8fd19d58ed3c', 'j4k5l6m7n8o9')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
