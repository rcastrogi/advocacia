"""Add template_content to petition_models

Revision ID: 20251227_194700
Revises: c59839edbece
Create Date: 2025-12-27 19:47:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251227_194700'
down_revision = 'c59839edbece'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar coluna template_content à tabela petition_models
    op.add_column('petition_models', sa.Column('template_content', sa.Text(), nullable=True))


def downgrade():
    # Remover coluna template_content da tabela petition_models
    op.drop_column('petition_models', 'template_content')
