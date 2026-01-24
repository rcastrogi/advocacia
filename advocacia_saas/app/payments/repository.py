"""
Payments Repository - Camada de acesso a dados
"""

from datetime import datetime, timedelta, timezone

# Decimal removed - unused
from typing import Any

from app import db
from app.models import (
    BillingPlan,
    Notification,
    Payment,
    PetitionBalanceTransaction,
    Subscription,
    User,
    UserPetitionBalance,
)


class PaymentRepository:
    """Repositório para operações com pagamentos"""

    @staticmethod
    def get_by_id(payment_id: int) -> Payment | None:
        return db.session.get(Payment, payment_id)

    @staticmethod
    def get_by_gateway_id(gateway_payment_id: str) -> Payment | None:
        return Payment.query.filter_by(gateway_payment_id=gateway_payment_id).first()

    @staticmethod
    def get_by_external_id(external_id: str) -> Payment | None:
        return Payment.query.filter_by(external_id=external_id).first()

    @staticmethod
    def get_user_payments(user_id: int, limit: int = 10) -> list[Payment]:
        return (
            Payment.query.filter_by(user_id=user_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(data: dict[str, Any]) -> Payment:
        payment = Payment(
            user_id=data["user_id"],
            amount=data["amount"],
            currency=data.get("currency", "BRL"),
            payment_type=data.get("payment_type", "one_time"),
            payment_method=data.get("payment_method", "pix"),
            status=data.get("status", "pending"),
            gateway=data.get("gateway", "mercadopago"),
            gateway_payment_id=data.get("gateway_payment_id"),
            external_id=data.get("external_id"),
            description=data.get("description"),
            pix_code=data.get("pix_code"),
            pix_qr_code=data.get("pix_qr_code"),
            pix_expires_at=data.get("pix_expires_at"),
            extra_data=data.get("extra_data"),
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    @staticmethod
    def update_status(payment: Payment, status: str) -> Payment:
        payment.status = status
        db.session.commit()
        return payment

    @staticmethod
    def mark_as_paid(payment: Payment) -> Payment:
        payment.mark_as_paid()
        return payment

    @staticmethod
    def update_extra_data(payment: Payment, extra_data: dict[str, Any]) -> Payment:
        payment.extra_data = {**(payment.extra_data or {}), **extra_data}
        db.session.commit()
        return payment


class SubscriptionRepository:
    """Repositório para assinaturas"""

    @staticmethod
    def get_by_id(subscription_id: int) -> Subscription | None:
        return db.session.get(Subscription, subscription_id)

    @staticmethod
    def get_active_by_user(user_id: int) -> Subscription | None:
        return Subscription.query.filter_by(user_id=user_id, status="active").first()

    @staticmethod
    def get_by_gateway_id(gateway_subscription_id: str) -> Subscription | None:
        return Subscription.query.filter_by(
            gateway_subscription_id=gateway_subscription_id
        ).first()

    @staticmethod
    def get_user_subscriptions(user_id: int) -> list[Subscription]:
        return (
            Subscription.query.filter_by(user_id=user_id)
            .order_by(Subscription.created_at.desc())
            .all()
        )

    @staticmethod
    def get_latest_by_user(user_id: int) -> Subscription | None:
        return (
            Subscription.query.filter_by(user_id=user_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

    @staticmethod
    def create(data: dict[str, Any]) -> Subscription:
        subscription = Subscription(
            user_id=data["user_id"],
            plan_type=data["plan_type"],
            billing_period=data.get("billing_period", "monthly"),
            amount=data["amount"],
            status=data.get("status", "pending"),
            gateway=data.get("gateway", "mercadopago"),
            gateway_subscription_id=data.get("gateway_subscription_id"),
            gateway_customer_id=data.get("gateway_customer_id"),
        )
        db.session.add(subscription)
        db.session.commit()
        return subscription

    @staticmethod
    def update_status(subscription: Subscription, status: str) -> Subscription:
        subscription.status = status
        db.session.commit()
        return subscription

    @staticmethod
    def activate(
        subscription: Subscription, billing_period: str = "monthly"
    ) -> Subscription:
        subscription.status = "active"
        subscription.started_at = datetime.now(timezone.utc)

        if billing_period == "monthly":
            subscription.renewal_date = datetime.now(timezone.utc) + timedelta(days=30)
        else:
            subscription.renewal_date = datetime.now(timezone.utc) + timedelta(days=365)

        db.session.commit()
        return subscription

    @staticmethod
    def cancel(subscription: Subscription) -> Subscription:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)
        db.session.commit()
        return subscription

    @staticmethod
    def count_active_by_user(user_id: int) -> int:
        return Subscription.query.filter_by(user_id=user_id, status="active").count()


class BillingPlanPaymentRepository:
    """Repositório para planos de pagamento"""

    @staticmethod
    def get_by_id(plan_id: int) -> BillingPlan | None:
        return db.session.get(BillingPlan, plan_id)

    @staticmethod
    def get_by_slug(slug: str, active_only: bool = True) -> BillingPlan | None:
        query = BillingPlan.query.filter_by(slug=slug)
        if active_only:
            query = query.filter_by(active=True)
        return query.first()

    @staticmethod
    def get_active_plans() -> list[BillingPlan]:
        return (
            BillingPlan.query.filter_by(active=True)
            .order_by(BillingPlan.plan_type, BillingPlan.name)
            .all()
        )


class BalanceRepository:
    """Repositório para saldo de petições"""

    @staticmethod
    def get_user_balance(user_id: int) -> UserPetitionBalance | None:
        return UserPetitionBalance.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_transactions(
        user_id: int, limit: int = 50
    ) -> list[PetitionBalanceTransaction]:
        return (
            PetitionBalanceTransaction.query.filter_by(user_id=user_id)
            .order_by(PetitionBalanceTransaction.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_transactions_paginated(user_id: int, page: int = 1, per_page: int = 20):
        return (
            PetitionBalanceTransaction.query.filter_by(user_id=user_id)
            .order_by(PetitionBalanceTransaction.created_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )


class NotificationRepository:
    """Repositório para notificações"""

    @staticmethod
    def create(data: dict[str, Any]) -> Notification:
        notification = Notification(
            user_id=data["user_id"],
            type=data.get("type", "info"),
            title=data["title"],
            message=data["message"],
            data=data.get("data"),
        )
        db.session.add(notification)
        db.session.commit()
        return notification


class UserPaymentRepository:
    """Repositório para operações de usuário relacionadas a pagamento"""

    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        return db.session.get(User, user_id)

    @staticmethod
    def update_billing_status(user: User, status: str) -> User:
        user.billing_status = status
        db.session.commit()
        return user
