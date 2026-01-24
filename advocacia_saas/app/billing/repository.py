"""
Billing Repository - Camada de acesso a dados
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from app import db
from app.models import (
    BillingPlan,
    Feature,
    PetitionType,
    PetitionUsage,
    User,
    UserPlan,
    plan_features as pf_table,
)


class BillingPlanRepository:
    """Repositório para operações com planos de cobrança"""

    @staticmethod
    def get_by_id(plan_id: int) -> BillingPlan | None:
        return db.session.get(BillingPlan, plan_id)

    @staticmethod
    def get_by_slug(slug: str) -> BillingPlan | None:
        return BillingPlan.query.filter_by(slug=slug).first()

    @staticmethod
    def get_active_plans() -> list[BillingPlan]:
        return (
            BillingPlan.query.filter_by(active=True)
            .order_by(BillingPlan.monthly_fee)
            .all()
        )

    @staticmethod
    def get_all_plans() -> list[BillingPlan]:
        return BillingPlan.query.order_by(BillingPlan.created_at.desc()).all()

    @staticmethod
    def create(data: dict[str, Any]) -> BillingPlan:
        plan = BillingPlan(
            slug=data["slug"],
            name=data["name"],
            description=data.get("description"),
            plan_type=data["plan_type"],
            monthly_fee=data.get("monthly_fee", Decimal("0.00")),
            monthly_petition_limit=data.get("monthly_petition_limit"),
            supported_periods=data.get("supported_periods", ["1m"]),
            discount_percentage=data.get("discount_percentage", Decimal("0.00")),
            active=data.get("active", True),
        )
        db.session.add(plan)
        db.session.commit()
        return plan

    @staticmethod
    def update(plan: BillingPlan, data: dict[str, Any]) -> BillingPlan:
        for key, value in data.items():
            if hasattr(plan, key):
                setattr(plan, key, value)
        db.session.commit()
        return plan

    @staticmethod
    def toggle_active(plan: BillingPlan) -> BillingPlan:
        plan.active = not plan.active
        db.session.commit()
        return plan


class PetitionTypeRepository:
    """Repositório para tipos de petição"""

    @staticmethod
    def get_by_id(type_id: int) -> PetitionType | None:
        return db.session.get(PetitionType, type_id)

    @staticmethod
    def get_by_slug(slug: str) -> PetitionType | None:
        return PetitionType.query.filter_by(slug=slug).first()

    @staticmethod
    def get_all() -> list[PetitionType]:
        return PetitionType.query.order_by(
            PetitionType.category, PetitionType.name
        ).all()

    @staticmethod
    def create(data: dict[str, Any]) -> PetitionType:
        petition_type = PetitionType(
            slug=data["slug"],
            name=data["name"],
            description=data.get("description"),
            category=data.get("category"),
            is_billable=data.get("is_billable", True),
            base_price=data.get("base_price"),
            active=data.get("active", True),
        )
        db.session.add(petition_type)
        db.session.commit()
        return petition_type

    @staticmethod
    def update(petition_type: PetitionType, data: dict[str, Any]) -> PetitionType:
        for key, value in data.items():
            if hasattr(petition_type, key):
                setattr(petition_type, key, value)
        db.session.commit()
        return petition_type

    @staticmethod
    def toggle_field(petition_type: PetitionType, field: str) -> PetitionType:
        if field == "is_billable":
            petition_type.is_billable = not petition_type.is_billable
        elif field == "active":
            petition_type.active = not petition_type.active
        db.session.commit()
        return petition_type


class UserPlanRepository:
    """Repositório para planos de usuário"""

    @staticmethod
    def get_active_plan(user_id: int) -> UserPlan | None:
        return UserPlan.query.filter_by(user_id=user_id, is_current=True).first()

    @staticmethod
    def get_user_plans(user_id: int) -> list[UserPlan]:
        return (
            UserPlan.query.filter_by(user_id=user_id)
            .order_by(UserPlan.started_at.desc())
            .all()
        )

    @staticmethod
    def assign_plan(user: User, plan: BillingPlan, status: str = "active") -> UserPlan:
        # Desativar planos atuais
        for user_plan in user.plans.filter_by(is_current=True).all():
            user_plan.is_current = False

        # Criar novo plano
        new_plan = UserPlan(
            user_id=user.id,
            plan_id=plan.id,
            status=status,
            started_at=datetime.utcnow(),
            renewal_date=datetime.utcnow() + timedelta(days=30),
            is_current=True,
        )
        db.session.add(new_plan)

        # Atualizar status do usuário
        user.billing_status = "delinquent" if status == "delinquent" else "active"
        db.session.commit()

        return new_plan

    @staticmethod
    def update_status(user_plan: UserPlan, status: str) -> UserPlan:
        user_plan.status = status
        db.session.commit()
        return user_plan


class PetitionUsageRepository:
    """Repositório para uso de petições"""

    @staticmethod
    def get_by_cycle(user_id: int, billing_cycle: str) -> list[PetitionUsage]:
        return (
            PetitionUsage.query.filter_by(user_id=user_id, billing_cycle=billing_cycle)
            .order_by(PetitionUsage.generated_at.desc())
            .all()
        )

    @staticmethod
    def get_usage_totals(usages: list[PetitionUsage]) -> dict[str, Any]:
        return {
            "count": len(usages),
            "billable": sum(1 for u in usages if u.billable),
            "billable_amount": sum((u.amount or 0) for u in usages if u.billable),
        }


class FeatureRepository:
    """Repositório para features"""

    @staticmethod
    def get_all_active() -> list[Feature]:
        return (
            Feature.query.filter_by(is_active=True)
            .order_by(Feature.module, Feature.display_order)
            .all()
        )

    @staticmethod
    def get_all() -> list[Feature]:
        return Feature.query.order_by(Feature.module, Feature.display_order).all()

    @staticmethod
    def get_by_id(feature_id: int) -> Feature | None:
        return db.session.get(Feature, feature_id)

    @staticmethod
    def get_plan_features(plan_id: int) -> dict[int, int | None]:
        """Retorna dict de feature_id -> limit_value para um plano"""
        result = db.session.execute(
            text(
                "SELECT feature_id, limit_value FROM plan_features WHERE plan_id = :plan_id"
            ),
            {"plan_id": plan_id},
        )
        return {row[0]: row[1] for row in result}

    @staticmethod
    def update_plan_features(
        plan_id: int, features_data: list[dict[str, Any]]
    ) -> None:
        """Atualiza features de um plano"""
        # Limpar features existentes
        db.session.execute(pf_table.delete().where(pf_table.c.plan_id == plan_id))

        # Adicionar novas
        for fd in features_data:
            db.session.execute(
                pf_table.insert().values(
                    plan_id=plan_id,
                    feature_id=fd["feature_id"],
                    limit_value=fd.get("limit_value"),
                )
            )

        db.session.commit()
