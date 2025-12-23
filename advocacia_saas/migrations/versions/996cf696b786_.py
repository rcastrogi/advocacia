"""empty message

Revision ID: 996cf696b786
Revises: 7a6c7aa40f2c, add_user_id_to_client
Create Date: 2025-12-23 07:21:41.590457

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '996cf696b786'
down_revision = ('7a6c7aa40f2c', 'add_user_id_to_client')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
