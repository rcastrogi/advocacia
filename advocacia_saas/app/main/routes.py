from datetime import datetime

from flask import render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.billing.decorators import subscription_required
from app.billing.utils import current_billing_cycle
from app.main import bp
from app.models import BillingPlan, Client, PetitionType, PetitionUsage
from app.quick_actions import build_dashboard_actions

# Ícones para categorias de petições
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


@bp.route("/")
def index():
    plans = _get_public_plans()
    petition_types = _get_implemented_petition_types()
    return render_template(
        "index.html",
        title="Petitio",
        pricing_plans=plans,
        petition_types=petition_types,
    )


@bp.route("/dashboard")
@login_required
def dashboard():
    # Get client statistics
    total_clients = Client.query.filter_by(lawyer_id=current_user.id).count()
    recent_clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.created_at.desc())
        .limit(5)
        .all()
    )

    stats = {"total_clients": total_clients, "recent_clients": recent_clients}
    quick_actions = _build_quick_actions_for(current_user)
    plan_summary = _build_plan_summary(current_user)

    return render_template(
        "dashboard.html",
        title="Dashboard",
        stats=stats,
        quick_actions=quick_actions,
        plan_summary=plan_summary,
    )


@bp.route("/peticionador")
@login_required
@subscription_required
def peticionador():
    return render_template("peticionador.html", title="Peticionador")


@bp.route("/termos")
def terms_of_service():
    """Página de Termos de Uso"""
    return render_template("terms_of_service.html", title="Termos de Uso")


@bp.route("/privacidade")
def privacy_policy():
    """Política de Privacidade em conformidade com LGPD"""
    return render_template("privacy_policy.html", title="Política de Privacidade")


@bp.route("/lgpd")
def lgpd_info():
    """Informações sobre conformidade com LGPD"""
    return render_template("lgpd_info.html", title="Conformidade LGPD")


def _build_quick_actions_for(user):
    return build_dashboard_actions(user.get_quick_actions())


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
    "01": "Jan",
    "02": "Fev",
    "03": "Mar",
    "04": "Abr",
    "05": "Mai",
    "06": "Jun",
    "07": "Jul",
    "08": "Ago",
    "09": "Set",
    "10": "Out",
    "11": "Nov",
    "12": "Dez",
}


def _build_plan_summary(user):
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
        summary["warning"] = (
            "Pagamento pendente detectado. Regularize para continuar gerando petições."
        )

    if not has_plan:
        summary.update(
            {
                "plan_name": None,
                "plan_type_label": None,
                "monthly_fee_display": "—",
                "usage_rate_display": "—",
                "cycle_usage_total": 0,
                "cycle_usage_amount_display": "R$ 0,00",
                "cycle_label": _current_cycle_label(),
                "started_at_label": None,
                "renewal_label": None,
            }
        )
        summary["empty_message"] = (
            "Você ainda não definiu um plano. Configure pagamentos para liberar todas as funcionalidades."
        )
        return summary

    plan = plan_rel.plan
    plan_type_label = PLAN_TYPE_LABELS.get(plan.plan_type, plan.plan_type.title())
    monthly_fee_display = _format_currency(plan.monthly_fee)
    usage_rate_display = _format_currency(plan.usage_rate)

    cycle = current_billing_cycle()
    cycle_label = _current_cycle_label(cycle)
    usage_total = PetitionUsage.query.filter_by(
        user_id=user.id, billing_cycle=cycle
    ).count()
    billable_amount = (
        db.session.query(func.coalesce(func.sum(PetitionUsage.amount), 0))
        .filter(
            PetitionUsage.user_id == user.id,
            PetitionUsage.billing_cycle == cycle,
            PetitionUsage.billable.is_(True),
        )
        .scalar()
    )

    summary.update(
        {
            "plan_name": plan.name,
            "plan_type_label": plan_type_label,
            "monthly_fee_display": monthly_fee_display,
            "usage_rate_display": usage_rate_display,
            "cycle_usage_total": usage_total,
            "cycle_usage_amount_display": _format_currency(billable_amount),
            "cycle_label": cycle_label,
            "started_at_label": _format_date(plan_rel.started_at),
            "renewal_label": _format_date(plan_rel.renewal_date),
        }
    )
    return summary


def _get_public_plans():
    plans = (
        BillingPlan.query.filter_by(active=True)
        .order_by(BillingPlan.plan_type, BillingPlan.name)
        .all()
    )
    public = []
    for plan in plans:
        public.append(
            {
                "name": plan.name,
                "description": plan.description,
                "plan_type_label": PLAN_TYPE_LABELS.get(
                    plan.plan_type, plan.plan_type.title()
                ),
                "monthly_fee": _format_currency(plan.monthly_fee),
                "usage_rate": _format_currency(plan.usage_rate),
                "is_per_usage": plan.plan_type == "per_usage",
            }
        )
    return public


def _format_currency(value):
    if not value:
        return "R$ 0,00"
    formatted = f"{value:,.2f}" if value else "0,00"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def _format_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _current_cycle_label(cycle=None):
    cycle = cycle or current_billing_cycle()
    year, month = cycle.split("-")
    month_label = MONTH_LABELS.get(month, month)
    return f"{month_label}/{year}"


def _get_implemented_petition_types():
    """Retorna os tipos de petição implementados para exibição pública."""
    types = (
        PetitionType.query.filter_by(is_implemented=True, active=True)
        .order_by(PetitionType.category, PetitionType.name)
        .all()
    )
    result = []
    for pt in types:
        result.append(
            {
                "id": pt.id,
                "name": pt.name,
                "description": pt.description or "Petição disponível para uso.",
                "category": pt.category,
                "category_label": CATEGORY_LABELS.get(pt.category, pt.category.title()),
                "icon": CATEGORY_ICONS.get(pt.category, "fa-file-alt"),
                "price": _format_currency(pt.base_price)
                if pt.is_billable
                else "Gratuito",
            }
        )
    return result
