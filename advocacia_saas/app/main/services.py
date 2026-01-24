"""
Main Services - Camada de lógica de negócios
"""

from datetime import datetime
from typing import Any

from flask import url_for

from app.billing.analytics import (
    get_monthly_usage_history,
    get_usage_insights,
    predict_limit_date,
)
from app.billing.utils import (
    current_billing_cycle,
    get_unread_notifications,
    get_user_petition_usage,
    mark_notification_as_read,
)
from app.main.repository import (
    BillingPlanRepository,
    ClientRepository,
    NotificationPreferencesRepository,
    NotificationRepository,
    PetitionTypeRepository,
    PetitionUsageRepository,
    RoadmapFeedbackRepository,
    RoadmapRepository,
    TablePreferenceRepository,
    TestimonialRepository,
)
from app.quick_actions import build_dashboard_actions


# Constantes
CATEGORY_ICONS = {
    "civel": "fa-balance-scale",
    "trabalhista": "fa-briefcase",
    "criminal": "fa-gavel",
    "previdenciario": "fa-user-shield",
    "tributario": "fa-file-invoice-dollar",
    "consumidor": "fa-shopping-cart",
    "familia": "fa-users",
    "administrativo": "fa-building",
}

CATEGORY_LABELS = {
    "civel": "Cível",
    "trabalhista": "Trabalhista",
    "criminal": "Criminal",
    "previdenciario": "Previdenciário",
    "tributario": "Tributário",
    "consumidor": "Consumidor",
    "familia": "Família",
    "administrativo": "Administrativo",
}

STATUS_BADGES = {
    "active": ("Plano ativo", "success"),
    "trial": ("Período de testes", "info"),
    "delinquent": ("Pagamento pendente", "danger"),
}

PLAN_TYPE_LABELS = {
    "per_usage": "Pague por uso",
    "monthly": "Mensalidade fixa",
}

MONTH_LABELS = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
}


class HomePageService:
    """Serviço para página inicial"""

    @staticmethod
    def get_index_data() -> dict[str, Any]:
        """Obtém todos os dados para a página inicial"""
        plans = HomePageService._get_public_plans()
        petition_types = HomePageService._get_implemented_petition_types()
        testimonials = TestimonialRepository.get_approved(limit=6)
        roadmap_data = HomePageService._get_roadmap_stats()

        return {
            "pricing_plans": plans,
            "petition_types": petition_types,
            "testimonials": testimonials,
            **roadmap_data,
        }

    @staticmethod
    def _get_public_plans() -> dict[str, list]:
        plans = BillingPlanRepository.get_active_plans()
        individual_plans = []
        office_plans = []

        for plan in plans:
            multi_users_limit = plan.get_feature_limit("multi_users")
            is_office_plan = multi_users_limit is not None and multi_users_limit > 1

            plan_data = {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "plan_type_label": PLAN_TYPE_LABELS.get(plan.plan_type, plan.plan_type.title()),
                "monthly_fee": FormatHelper.format_currency(plan.monthly_fee),
                "monthly_fee_raw": plan.monthly_fee or 0,
                "is_per_usage": plan.plan_type == "per_usage",
                "is_office_plan": is_office_plan,
                "max_users": multi_users_limit or 1,
                "features": plan.features,
                "get_feature_limit": plan.get_feature_limit,
            }

            if is_office_plan:
                office_plans.append(plan_data)
            else:
                individual_plans.append(plan_data)

        return {
            "individual": individual_plans,
            "office": office_plans,
            "all": individual_plans + office_plans,
        }

    @staticmethod
    def _get_implemented_petition_types() -> list[dict]:
        types = PetitionTypeRepository.get_implemented()
        result = []
        for pt in types:
            result.append({
                "id": pt.id,
                "name": pt.name,
                "description": pt.description or "Petição disponível para uso.",
                "category": pt.category,
                "category_label": CATEGORY_LABELS.get(pt.category, pt.category.title()),
                "icon": CATEGORY_ICONS.get(pt.category, "fa-file-alt"),
                "price": FormatHelper.format_currency(pt.base_price) if pt.is_billable else "Gratuito",
            })
        return result

    @staticmethod
    def _get_roadmap_stats() -> dict[str, Any]:
        public_items = RoadmapRepository.get_public_items()

        stats = {
            "total": len(public_items),
            "completed": len([i for i in public_items if i.status == "completed"]),
            "in_progress": len([i for i in public_items if i.status == "in_progress"]),
            "planned": len([i for i in public_items if i.status == "planned"]),
        }

        if stats["total"] > 0:
            stats["progress"] = round((stats["completed"] / stats["total"]) * 100, 1)
        else:
            stats["progress"] = 0

        # Items em destaque
        featured = []
        featured.extend(RoadmapRepository.get_completed_items(3))
        featured.extend(RoadmapRepository.get_in_progress_items(3))
        planned = RoadmapRepository.get_planned_items(6)
        featured.extend(planned)

        return {
            "roadmap_stats": stats,
            "featured_roadmap": featured,
            "planned_roadmap": planned,
        }


class DashboardService:
    """Serviço para dashboard do usuário"""

    @staticmethod
    def get_dashboard_data(user) -> dict[str, Any]:
        """Obtém todos os dados para o dashboard"""
        total_clients = ClientRepository.count_by_lawyer(user.id)
        recent_clients = ClientRepository.get_recent_by_lawyer(user.id)

        stats = {
            "total_clients": total_clients,
            "recent_clients": recent_clients,
        }

        quick_actions = build_dashboard_actions(user.get_quick_actions())
        plan_summary = PlanSummaryService.build_plan_summary(user)
        petition_usage = get_user_petition_usage(user)
        usage_history = get_monthly_usage_history(user, months=6)
        prediction = predict_limit_date(user)
        insights = get_usage_insights(user)
        notifications = get_unread_notifications(user)

        return {
            "stats": stats,
            "quick_actions": quick_actions,
            "plan_summary": plan_summary,
            "petition_usage": petition_usage,
            "usage_history": usage_history,
            "prediction": prediction,
            "insights": insights,
            "notifications": notifications,
        }


class PlanSummaryService:
    """Serviço para resumo do plano"""

    @staticmethod
    def build_plan_summary(user) -> dict[str, Any]:
        plan_rel = user.get_active_plan()
        has_plan = plan_rel is not None
        status_label, badge_variant = STATUS_BADGES.get(
            user.billing_status, ("Status indefinido", "secondary")
        )

        summary = {
            "has_plan": has_plan,
            "status_label": status_label,
            "status_badge": badge_variant,
            "manage_url": url_for("billing.portal"),
            "warning": None,
        }

        if user.billing_status == "delinquent":
            summary["warning"] = "Pagamento pendente detectado. Regularize para continuar gerando petições."

        if user.trial_active:
            if user.is_trial_expired:
                summary["warning"] = "Seu período de teste expirou. Assine um plano para continuar usando o sistema."
            else:
                summary["trial_info"] = {
                    "days_remaining": user.trial_days_remaining,
                    "message": f"Você está em período de teste com {user.trial_days_remaining} dias restantes.",
                }

        if not has_plan:
            summary.update({
                "plan_name": None,
                "plan_type_label": None,
                "monthly_fee_display": "—",
                "usage_rate_display": "—",
                "cycle_usage_total": 0,
                "cycle_usage_amount_display": "R$ 0,00",
                "cycle_label": FormatHelper.current_cycle_label(),
                "started_at_label": None,
                "renewal_label": None,
            })
            summary["empty_message"] = "Você ainda não definiu um plano. Configure pagamentos para liberar todas as funcionalidades."
            return summary

        plan = plan_rel.plan
        cycle = current_billing_cycle()

        summary.update({
            "plan_name": plan.name,
            "plan_type_label": PLAN_TYPE_LABELS.get(plan.plan_type, plan.plan_type.title()),
            "monthly_fee_display": FormatHelper.format_currency(plan.monthly_fee),
            "cycle_usage_total": PetitionUsageRepository.count_by_cycle(user.id, cycle),
            "cycle_usage_amount_display": FormatHelper.format_currency(
                PetitionUsageRepository.get_billable_amount(user.id, cycle)
            ),
            "cycle_label": FormatHelper.current_cycle_label(cycle),
            "started_at_label": FormatHelper.format_date(plan_rel.started_at),
            "renewal_label": FormatHelper.format_date(plan_rel.renewal_date),
        })

        return summary


class TestimonialService:
    """Serviço para depoimentos"""

    @staticmethod
    def get_user_testimonials(user_id: int) -> list:
        return TestimonialRepository.get_by_user(user_id)

    @staticmethod
    def create(user_id: int, form_data: dict[str, Any]):
        return TestimonialRepository.create({
            "user_id": user_id,
            "content": form_data["content"].strip(),
            "rating": int(form_data["rating"]),
            "display_name": form_data["display_name"].strip(),
            "display_role": form_data.get("display_role", "").strip() or None,
            "display_location": form_data.get("display_location", "").strip() or None,
        })

    @staticmethod
    def update(testimonial, form_data: dict[str, Any]):
        return TestimonialRepository.update(testimonial, {
            "content": form_data["content"].strip(),
            "rating": int(form_data["rating"]),
            "display_name": form_data["display_name"].strip(),
            "display_role": form_data.get("display_role", "").strip() or None,
            "display_location": form_data.get("display_location", "").strip() or None,
        })

    @staticmethod
    def delete(testimonial):
        TestimonialRepository.delete(testimonial)

    @staticmethod
    def can_edit(testimonial, user_id: int) -> bool:
        return testimonial.user_id == user_id and testimonial.status == "pending"

    @staticmethod
    def can_delete(testimonial, user_id: int) -> bool:
        return testimonial.user_id == user_id


class TestimonialAdminService:
    """Serviço admin para depoimentos"""

    @staticmethod
    def get_all_with_counts(status_filter: str | None = None) -> dict[str, Any]:
        testimonials = TestimonialRepository.get_all_with_filter(status_filter)
        counts = TestimonialRepository.get_counts()
        return {"testimonials": testimonials, "counts": counts}

    @staticmethod
    def moderate(testimonial, action: str, moderator_id: int, rejection_reason: str | None = None):
        return TestimonialRepository.moderate(testimonial, action, moderator_id, rejection_reason)


class RoadmapService:
    """Serviço para roadmap público"""

    @staticmethod
    def get_roadmap_page_data() -> dict[str, Any]:
        public_items = RoadmapRepository.get_public_items()

        completed = [i for i in public_items if i.status == "completed"]
        pending = [i for i in public_items if i.status in ["planned", "in_progress"]]

        # Agrupar por categoria
        completed_categories = RoadmapService._group_by_category(completed)
        pending_categories = RoadmapService._group_by_category(pending)

        total = len(public_items)
        completed_count = len(completed)
        in_progress = len([i for i in public_items if i.status == "in_progress"])
        planned = len([i for i in public_items if i.status == "planned"])

        progress = (completed_count / total * 100) if total > 0 else 0

        return {
            "completed_categories": completed_categories,
            "pending_categories": pending_categories,
            "total_features": total,
            "completed_features": completed_count,
            "in_progress_features": in_progress,
            "planned_features": planned,
            "overall_progress": round(progress, 1),
        }

    @staticmethod
    def _group_by_category(items: list) -> list[dict]:
        categories = {}
        for item in items:
            cat_slug = item.category.slug
            if cat_slug not in categories:
                categories[cat_slug] = {"category": item.category, "items": []}
            categories[cat_slug]["items"].append(item)

        return sorted(categories.values(), key=lambda x: x["category"].order)

    @staticmethod
    def get_item_detail(slug: str) -> dict[str, Any] | None:
        item = RoadmapRepository.get_by_slug(slug)
        if not item:
            return None

        related = RoadmapRepository.get_related_items(item)
        return {"item": item, "related_items": related}


class RoadmapFeedbackService:
    """Serviço para feedback do roadmap"""

    @staticmethod
    def get_existing_feedback(user_id: int, item_id: int):
        return RoadmapFeedbackRepository.get_by_user_and_item(user_id, item_id)

    @staticmethod
    def submit_feedback(data: dict[str, Any], existing_feedback=None) -> tuple[bool, str]:
        """Cria ou atualiza feedback"""
        rating = data.get("rating", 5)
        if not 1 <= rating <= 5:
            return False, "Avaliação deve ser entre 1 e 5 estrelas."

        if existing_feedback:
            RoadmapFeedbackRepository.update(existing_feedback, data)
            return True, "Seu feedback foi atualizado com sucesso!"
        else:
            RoadmapFeedbackRepository.create(data)
            return True, "Obrigado pelo seu feedback! Ele nos ajuda a melhorar continuamente."


class NotificationService:
    """Serviço para notificações"""

    @staticmethod
    def get_user_notifications(user_id: int) -> dict[str, Any]:
        notifications = NotificationRepository.get_by_user(user_id)
        unread_count = sum(1 for n in notifications if not n.read)
        return {"notifications": notifications, "unread_count": unread_count}

    @staticmethod
    def mark_as_read(notification_id: int, user) -> bool:
        return mark_notification_as_read(notification_id, user)

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        return NotificationRepository.mark_all_as_read(user_id)


class NotificationPreferencesService:
    """Serviço para preferências de notificação"""

    @staticmethod
    def get_or_create(user_id: int):
        return NotificationPreferencesRepository.get_or_create(user_id)

    @staticmethod
    def update_from_form(prefs, form) -> None:
        data = {
            "email_enabled": form.email_enabled.data,
            "push_enabled": form.push_enabled.data,
            "in_app_enabled": form.in_app_enabled.data,
            "deadline_email": form.deadline_email.data,
            "deadline_push": form.deadline_push.data,
            "deadline_in_app": form.deadline_in_app.data,
            "movement_email": form.movement_email.data,
            "movement_push": form.movement_push.data,
            "movement_in_app": form.movement_in_app.data,
            "payment_email": form.payment_email.data,
            "payment_push": form.payment_push.data,
            "payment_in_app": form.payment_in_app.data,
            "petition_email": form.petition_email.data,
            "petition_push": form.petition_push.data,
            "petition_in_app": form.petition_in_app.data,
            "system_email": form.system_email.data,
            "system_push": form.system_push.data,
            "system_in_app": form.system_in_app.data,
            "quiet_hours_enabled": form.quiet_hours_enabled.data,
            "quiet_hours_start": form.quiet_hours_start.data,
            "quiet_hours_end": form.quiet_hours_end.data,
            "quiet_hours_weekends": form.quiet_hours_weekends.data,
            "digest_enabled": form.digest_enabled.data,
            "digest_frequency": form.digest_frequency.data,
            "digest_time": form.digest_time.data,
            "min_priority_email": int(form.min_priority_email.data),
            "min_priority_push": int(form.min_priority_push.data),
        }
        NotificationPreferencesRepository.update(prefs, data)


class UserPreferencesService:
    """Serviço para preferências do usuário"""

    @staticmethod
    def get_table_preferences(user_id: int, view_key: str) -> dict | None:
        return TablePreferenceRepository.get_for_user(user_id, view_key)

    @staticmethod
    def save_table_preferences(user_id: int, view_key: str, preferences: dict) -> None:
        TablePreferenceRepository.set_for_user(user_id, view_key, preferences)


class FormatHelper:
    """Helpers de formatação"""

    @staticmethod
    def format_currency(value) -> str:
        if not value:
            return "R$ 0,00"
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    @staticmethod
    def format_date(value) -> str | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y")
        return str(value)

    @staticmethod
    def current_cycle_label(cycle: str | None = None) -> str:
        cycle = cycle or current_billing_cycle()
        year, month = cycle.split("-")
        month_label = MONTH_LABELS.get(month, month)
        return f"{month_label}/{year}"
