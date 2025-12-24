"""Merge migration heads

Revision ID: 7605f8df8a9f
Revises: 01bc3ed79a56, i9j0k1l2m3n4
Create Date: 2025-12-24 18:50:32.478782

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7605f8df8a9f'
down_revision = ('01bc3ed79a56', 'i9j0k1l2m3n4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
