"""Add Office and OfficeInvite models

Revision ID: 20260110_office
Revises: 6ccd19e0e1f2
Create Date: 2026-01-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260110_office"
down_revision = "6ccd19e0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    # Criar tabela offices primeiro
    op.create_table(
        "offices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("cnpj", sa.String(length=20), nullable=True),
        sa.Column("oab_number", sa.String(length=50), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("website", sa.String(length=200), nullable=True),
        sa.Column("cep", sa.String(length=10), nullable=True),
        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("complement", sa.String(length=200), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("uf", sa.String(length=2), nullable=True),
        sa.Column("logo_filename", sa.String(length=200), nullable=True),
        sa.Column(
            "primary_color",
            sa.String(length=7),
            nullable=True,
            server_default="#1a73e8",
        ),
        sa.Column("settings", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # Criar índice para owner_id
    op.create_index("ix_offices_owner_id", "offices", ["owner_id"])

    # Adicionar foreign key para owner_id após criar a tabela
    op.create_foreign_key(
        "fk_offices_owner_id", "offices", "user", ["owner_id"], ["id"]
    )

    # Adicionar colunas office_id e office_role na tabela user
    op.add_column("user", sa.Column("office_id", sa.Integer(), nullable=True))
    op.add_column(
        "user",
        sa.Column(
            "office_role", sa.String(length=20), nullable=True, server_default="lawyer"
        ),
    )
    op.create_index("ix_user_office_id", "user", ["office_id"])
    op.create_foreign_key("fk_user_office_id", "user", "offices", ["office_id"], ["id"])

    # Criar tabela office_invites
    op.create_table(
        "office_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("office_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column(
            "role", sa.String(length=20), nullable=False, server_default="lawyer"
        ),
        sa.Column("token", sa.String(length=100), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invited_by_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["office_id"],
            ["offices.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_office_invites_email", "office_invites", ["email"])
    op.create_index("ix_office_invites_token", "office_invites", ["token"])


def downgrade():
    # Remover tabela office_invites
    op.drop_index("ix_office_invites_token", table_name="office_invites")
    op.drop_index("ix_office_invites_email", table_name="office_invites")
    op.drop_table("office_invites")

    # Remover colunas da tabela user
    op.drop_constraint("fk_user_office_id", "user", type_="foreignkey")
    op.drop_index("ix_user_office_id", table_name="user")
    op.drop_column("user", "office_role")
    op.drop_column("user", "office_id")

    # Remover tabela offices
    op.drop_constraint("fk_offices_owner_id", "offices", type_="foreignkey")
    op.drop_index("ix_offices_owner_id", table_name="offices")
    op.drop_table("offices")
