"""Add show_new_badge to RoadmapItem

Revision ID: j4k5l6m7n8o9
Revises: i9j0k1l2m3n4
Create Date: 2025-12-31 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "j4k5l6m7n8o9"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "roadmap_items",
        sa.Column("show_new_badge", sa.Boolean(), nullable=True, default=False),
    )


def downgrade() -> None:
    op.drop_column("roadmap_items", "show_new_badge")