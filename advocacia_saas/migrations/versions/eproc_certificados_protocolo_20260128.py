"""add advogado_certificados table and protocol fields to saved_petitions

Revision ID: eproc_certificados_protocolo_20260128
Revises: fee_contract_templates_20260127
Create Date: 2026-01-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eproc_certificados_protocolo_20260128"
down_revision = "fee_contract_templates_20260127"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Criar tabela advogado_certificados
    op.create_table(
        "advogado_certificados",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        # Identificação
        sa.Column("nome_titular", sa.String(length=300), nullable=True),
        sa.Column("oab_numero", sa.String(length=20), nullable=True),
        sa.Column("oab_uf", sa.String(length=2), nullable=True),
        sa.Column("cpf", sa.String(length=14), nullable=True),
        sa.Column("emissor", sa.String(length=300), nullable=True),
        sa.Column("numero_serie", sa.String(length=100), nullable=True),
        # Certificado criptografado
        sa.Column("certificado_pfx", sa.LargeBinary(), nullable=True),
        sa.Column("certificado_hash", sa.String(length=64), nullable=True),
        # Senha cifrada (opcional)
        sa.Column("senha_cifrada", sa.LargeBinary(), nullable=True),
        # Validade
        sa.Column("validade_inicio", sa.DateTime(), nullable=True),
        sa.Column("validade_fim", sa.DateTime(), nullable=True),
        # Status
        sa.Column("ativo", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("apelido", sa.String(length=100), nullable=True),
        # Auditoria
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("ultimo_uso", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_advogado_certificados_user_id",
        "advogado_certificados",
        ["user_id"],
    )

    # 2. Adicionar campos de protocolo à tabela saved_petitions
    op.add_column(
        "saved_petitions",
        sa.Column("protocolo_numero", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "saved_petitions",
        sa.Column("protocolo_data", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "saved_petitions",
        sa.Column("protocolo_tribunal", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "saved_petitions",
        sa.Column(
            "protocolo_status",
            sa.String(length=30),
            nullable=True,
            server_default="nao_protocolado",
        ),
    )
    op.add_column(
        "saved_petitions",
        sa.Column("protocolo_erro", sa.Text(), nullable=True),
    )
    op.add_column(
        "saved_petitions",
        sa.Column(
            "protocolo_certificado_id",
            sa.Integer(),
            sa.ForeignKey("advogado_certificados.id"),
            nullable=True,
        ),
    )


def downgrade():
    # Remove protocol columns from saved_petitions
    op.drop_column("saved_petitions", "protocolo_certificado_id")
    op.drop_column("saved_petitions", "protocolo_erro")
    op.drop_column("saved_petitions", "protocolo_status")
    op.drop_column("saved_petitions", "protocolo_tribunal")
    op.drop_column("saved_petitions", "protocolo_data")
    op.drop_column("saved_petitions", "protocolo_numero")

    # Drop advogado_certificados table
    op.drop_index("ix_advogado_certificados_user_id", table_name="advogado_certificados")
    op.drop_table("advogado_certificados")
