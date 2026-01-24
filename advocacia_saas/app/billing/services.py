"""
Billing Services - Camada de lógica de negócios
"""

from decimal import Decimal
from typing import Any

from flask import abort

from app.billing.repository import (
    BillingPlanRepository,
    FeatureRepository,
    PetitionTypeRepository,
    PetitionUsageRepository,
    UserPlanRepository,
)
from app.billing.utils import current_billing_cycle, slugify
from app.models import BillingPlan, PetitionType, User


class BillingPortalService:
    """Serviço para portal de billing do usuário"""

    @staticmethod
    def get_user_billing_info(user: User) -> dict[str, Any]:
        """Obtém informações de billing do usuário"""
        plan = user.get_active_plan()
        cycle = current_billing_cycle()
        usages = PetitionUsageRepository.get_by_cycle(user.id, cycle)
        totals = PetitionUsageRepository.get_usage_totals(usages)

        return {
            "plan": plan,
            "cycle": cycle,
            "usages": usages,
            "totals": totals,
        }

    @staticmethod
    def get_upgrade_options(user: User) -> dict[str, Any]:
        """Obtém opções de upgrade para o usuário"""
        current_plan = user.get_active_plan()
        available_plans = BillingPlanRepository.get_active_plans()

        # Filtrar planos por uso e remover plano atual
        available_plans = [p for p in available_plans if p.plan_type != "per_usage"]
        if current_plan:
            available_plans = [p for p in available_plans if p.id != current_plan.plan.id]

        return {
            "current_plan": current_plan,
            "available_plans": available_plans,
        }


class PetitionTypeService:
    """Serviço para tipos de petição"""

    @staticmethod
    def list_all() -> list[PetitionType]:
        return PetitionTypeRepository.get_all()

    @staticmethod
    def create(form_data: dict[str, Any]) -> tuple[PetitionType | None, str | None]:
        """Cria um novo tipo de petição"""
        slug = slugify(form_data["name"])

        # Verificar duplicata
        if PetitionTypeRepository.get_by_slug(slug):
            return None, "Já existe um tipo com este nome/slug."

        petition_type = PetitionTypeRepository.create({
            "slug": slug,
            "name": form_data["name"],
            "description": form_data.get("description"),
            "category": form_data.get("category"),
            "is_billable": form_data.get("is_billable", True),
            "base_price": form_data.get("base_price"),
            "active": form_data.get("active", True),
        })

        return petition_type, None

    @staticmethod
    def update(
        type_id: int, form_data: dict[str, Any]
    ) -> tuple[PetitionType | None, str | None]:
        """Atualiza um tipo de petição"""
        petition_type = PetitionTypeRepository.get_by_id(type_id)
        if not petition_type:
            return None, "Tipo de petição não encontrado."

        new_slug = slugify(form_data["name"])

        # Verificar duplicata (exceto o próprio)
        existing = PetitionTypeRepository.get_by_slug(new_slug)
        if existing and existing.id != type_id:
            return None, "Outro tipo já usa este nome/slug."

        PetitionTypeRepository.update(petition_type, {
            "slug": new_slug,
            "name": form_data["name"],
            "description": form_data.get("description"),
            "category": form_data.get("category"),
            "is_billable": form_data.get("is_billable", True),
            "base_price": form_data.get("base_price"),
            "active": form_data.get("active", True),
        })

        return petition_type, None

    @staticmethod
    def toggle(type_id: int, action: str) -> PetitionType:
        """Alterna campo de um tipo de petição"""
        petition_type = PetitionTypeRepository.get_by_id(type_id)
        if not petition_type:
            abort(404)

        field = "is_billable" if action == "toggle_billable" else "active"
        PetitionTypeRepository.toggle_field(petition_type, field)
        return petition_type


class BillingPlanService:
    """Serviço para planos de cobrança"""

    @staticmethod
    def list_all() -> list[BillingPlan]:
        return BillingPlanRepository.get_all_plans()

    @staticmethod
    def list_active() -> list[BillingPlan]:
        return BillingPlanRepository.get_active_plans()

    @staticmethod
    def get_by_id(plan_id: int) -> BillingPlan:
        plan = BillingPlanRepository.get_by_id(plan_id)
        if not plan:
            abort(404)
        return plan

    @staticmethod
    def create(form_data: dict[str, Any]) -> tuple[BillingPlan | None, str | None]:
        """Cria um novo plano"""
        slug = slugify(form_data["name"])

        # Verificar duplicata
        if BillingPlanRepository.get_by_slug(slug):
            return None, "Já existe um plano com este nome."

        # Processar limite de petições
        monthly_limit = form_data.get("monthly_petition_limit")
        if monthly_limit and isinstance(monthly_limit, str) and monthly_limit.isdigit():
            monthly_limit = int(monthly_limit)
        else:
            monthly_limit = None

        plan = BillingPlanRepository.create({
            "slug": slug,
            "name": form_data["name"],
            "description": form_data.get("description"),
            "plan_type": form_data["plan_type"],
            "monthly_fee": form_data.get("monthly_fee") or Decimal("0.00"),
            "monthly_petition_limit": monthly_limit,
            "supported_periods": form_data.get("supported_periods", ["1m"]),
            "discount_percentage": form_data.get("discount_percentage") or Decimal("0.00"),
            "active": form_data.get("active", True),
        })

        return plan, None

    @staticmethod
    def update(
        plan_id: int, form_data: dict[str, Any]
    ) -> tuple[BillingPlan | None, str | None]:
        """Atualiza um plano"""
        plan = BillingPlanRepository.get_by_id(plan_id)
        if not plan:
            return None, "Plano não encontrado."

        new_slug = slugify(form_data["name"])

        # Verificar duplicata (exceto o próprio)
        existing = BillingPlanRepository.get_by_slug(new_slug)
        if existing and existing.id != plan_id:
            return None, "Já existe um plano com este nome."

        # Processar limite de petições
        monthly_limit = form_data.get("monthly_petition_limit")
        if monthly_limit and isinstance(monthly_limit, str) and monthly_limit.isdigit():
            monthly_limit = int(monthly_limit)
        else:
            monthly_limit = None

        BillingPlanRepository.update(plan, {
            "slug": new_slug,
            "name": form_data["name"],
            "description": form_data.get("description"),
            "plan_type": form_data["plan_type"],
            "monthly_fee": form_data.get("monthly_fee") or Decimal("0.00"),
            "monthly_petition_limit": monthly_limit,
            "supported_periods": form_data.get("supported_periods", ["1m"]),
            "discount_percentage": form_data.get("discount_percentage") or Decimal("0.00"),
            "active": form_data.get("active", True),
        })

        return plan, None

    @staticmethod
    def toggle_active(plan_id: int) -> BillingPlan:
        """Alterna status ativo de um plano"""
        plan = BillingPlanRepository.get_by_id(plan_id)
        if not plan:
            abort(404)
        BillingPlanRepository.toggle_active(plan)
        return plan


class UserPlanService:
    """Serviço para gerenciamento de planos de usuário"""

    @staticmethod
    def change_billing_status(user: User, status: str) -> bool:
        """Altera status de billing do usuário"""
        if status not in {"active", "trial", "delinquent"}:
            return False

        user.billing_status = status
        plan = user.get_active_plan()
        if plan:
            plan.status = status

        from app import db
        db.session.commit()
        return True

    @staticmethod
    def change_plan_status(user: User, status: str) -> tuple[bool, str | None]:
        """Altera status do plano do usuário"""
        if status not in {"active", "trial", "delinquent"}:
            return False, "Status inválido."

        plan = user.get_active_plan()
        if not plan:
            return False, "Usuário não possui plano atual."

        UserPlanRepository.update_status(plan, status)

        if status == "delinquent":
            user.billing_status = "delinquent"
        elif user.billing_status != "delinquent":
            user.billing_status = status

        from app import db
        db.session.commit()
        return True, None

    @staticmethod
    def assign_plan(user: User, plan_id: int, status: str = "active") -> tuple[bool, str | None]:
        """Atribui um plano a um usuário"""
        plan = BillingPlanRepository.get_by_id(plan_id)
        if not plan:
            return False, "Plano não encontrado."

        UserPlanRepository.assign_plan(user, plan, status)
        return True, None


class FeatureService:
    """Serviço para features modulares"""

    @staticmethod
    def list_all_grouped() -> dict[str, list[Any]]:
        """Lista features agrupadas por módulo"""
        features = FeatureRepository.get_all()
        modules: dict[str, list[Any]] = {}
        for feature in features:
            if feature.module not in modules:
                modules[feature.module] = []
            modules[feature.module].append(feature)
        return modules

    @staticmethod
    def list_active() -> list[Any]:
        return FeatureRepository.get_all_active()

    @staticmethod
    def get_plan_features_grouped(plan_id: int) -> dict[str, list[dict[str, Any]]]:
        """Obtém features de um plano agrupadas por módulo"""
        all_features = FeatureRepository.get_all_active()
        current_features = FeatureRepository.get_plan_features(plan_id)

        modules: dict[str, list[dict[str, Any]]] = {}
        for feature in all_features:
            if feature.module not in modules:
                modules[feature.module] = []
            modules[feature.module].append({
                "feature": feature,
                "selected": feature.id in current_features,
                "limit": current_features.get(feature.id),
            })

        return modules

    @staticmethod
    def update_plan_features(plan_id: int, selected_features: list[str], limits: dict[str, str]) -> None:
        """Atualiza features de um plano"""
        features_data = []
        for feature_id_str in selected_features:
            feature_id = int(feature_id_str)
            limit_value = limits.get(f"limit_{feature_id}")
            limit_int = int(limit_value) if limit_value and limit_value.isdigit() else None

            features_data.append({
                "feature_id": feature_id,
                "limit_value": limit_int,
            })

        FeatureRepository.update_plan_features(plan_id, features_data)
