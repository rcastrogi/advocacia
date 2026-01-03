"""add quick action preferences to user

Revision ID: 5d4c0b8d1bb6
Revises: 7605f8df8a9f
Create Date: 2025-11-23 00:00:00.000000
"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5d4c0b8d1bb6"
down_revision = "7605f8df8a9f"
branch_labels = None
depends_on = None

DEFAULT_ACTIONS = json.dumps(
    [
        "clients_new",
        "petitions_civil",
        "petitions_family",
        "clients_search",
    ]
)


def upgrade() -> None:
    op.add_column("user", sa.Column("quick_actions", sa.Text(), nullable=True))
    conn = op.get_bind()
    conn.execute(
        sa.text(
            'UPDATE "user" SET quick_actions = :default WHERE quick_actions IS NULL'
        ),
        {"default": DEFAULT_ACTIONS},
    )


def downgrade() -> None:
    op.drop_column("user", "quick_actions")
