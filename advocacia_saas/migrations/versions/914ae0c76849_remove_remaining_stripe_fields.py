"""Remove remaining Stripe fields

Revision ID: 914ae0c76849
Revises: 7605f8df8a9f
Create Date: 2025-12-24 18:50:49.238179

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "914ae0c76849"
down_revision = "7605f8df8a9f"
branch_labels = None
depends_on = None


def upgrade():
    # Remove stripe_customer_id from user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_stripe_customer_id"))
        batch_op.drop_column("stripe_customer_id")

    # Remove Stripe fields from payments table
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_payments_stripe_subscription_id"))
        batch_op.drop_index(batch_op.f("ix_payments_stripe_payment_intent_id"))
        batch_op.drop_index(batch_op.f("ix_payments_stripe_customer_id"))
        batch_op.drop_index(batch_op.f("ix_payments_stripe_checkout_session_id"))
        batch_op.drop_column("stripe_subscription_id")
        batch_op.drop_column("stripe_payment_intent_id")
        batch_op.drop_column("stripe_checkout_session_id")
        batch_op.drop_column("stripe_customer_id")

    # Remove stripe_price_id from credit_packages table
    with op.batch_alter_table("credit_packages", schema=None) as batch_op:
        batch_op.drop_column("stripe_price_id")

    # Remove payment_intent_id from credit_transactions table
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        batch_op.drop_column("payment_intent_id")


def downgrade():
    # Add back stripe_price_id to credit_packages table
    with op.batch_alter_table("credit_packages", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("stripe_price_id", sa.String(length=100), nullable=True)
        )

    # Add back payment_intent_id to credit_transactions table
    with op.batch_alter_table("credit_transactions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("payment_intent_id", sa.String(length=100), nullable=True)
        )

    # Add back Stripe fields to payments table
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("stripe_customer_id", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(
            sa.Column("stripe_payment_intent_id", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "stripe_checkout_session_id", sa.String(length=120), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("stripe_subscription_id", sa.String(length=120), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_payments_stripe_checkout_session_id"),
            ["stripe_checkout_session_id"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_payments_stripe_customer_id"),
            ["stripe_customer_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_payments_stripe_payment_intent_id"),
            ["stripe_payment_intent_id"],
            unique=True,
        )
        batch_op.create_index(
            batch_op.f("ix_payments_stripe_subscription_id"),
            ["stripe_subscription_id"],
            unique=False,
        )

    # Add back stripe_customer_id to user table
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("stripe_customer_id", sa.String(length=120), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_user_stripe_customer_id"),
            ["stripe_customer_id"],
            unique=True,
        )
