"""Add 2FA fields to User model

Revision ID: c59839edbece
Revises: 9204bd05a89e
Create Date: 2025-12-24 20:33:14.900613

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c59839edbece'
down_revision = '9204bd05a89e'
branch_labels = None
depends_on = None


def upgrade():
    # Add 2FA fields to user table
    op.add_column('user', sa.Column('two_factor_enabled', sa.Boolean(), nullable=True, default=False))
    op.add_column('user', sa.Column('two_factor_method', sa.String(length=20), nullable=True))
    op.add_column('user', sa.Column('totp_secret', sa.String(length=32), nullable=True))
    op.add_column('user', sa.Column('two_factor_backup_codes', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('two_factor_last_used', sa.DateTime(), nullable=True))


def downgrade():
    # Remove 2FA fields from user table
    op.drop_column('user', 'two_factor_last_used')
    op.drop_column('user', 'two_factor_backup_codes')
    op.drop_column('user', 'totp_secret')
    op.drop_column('user', 'two_factor_method')
    op.drop_column('user', 'two_factor_enabled')
