"""
Funções para análise e previsão de uso de petições
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import extract, func

from app.models import PetitionUsage


def get_monthly_usage_history(user, months=6):
    """Retorna histórico de uso de petições nos últimos N meses."""
    history = []
    current_date = datetime.now(timezone.utc)

    for i in range(months):
        month_date = current_date - timedelta(days=30 * i)
        cycle = month_date.strftime("%Y-%m")

        # Contar apenas billable
        billable_count = PetitionUsage.query.filter_by(
            user_id=user.id,
            billing_cycle=cycle,
            billable=True,
        ).count()

        # Total incluindo gratuitas
        total_count = PetitionUsage.query.filter_by(
            user_id=user.id,
            billing_cycle=cycle,
        ).count()

        history.append(
            {
                "cycle": cycle,
                "month_name": month_date.strftime("%b/%Y"),
                "billable": billable_count,
                "free": total_count - billable_count,
                "total": total_count,
            }
        )

    return list(reversed(history))  # Mais antigo primeiro


def predict_limit_date(user):
    """Prevê quando o usuário atingirá o limite baseado no uso atual."""
    plan = user.get_active_plan()

    if not plan or plan.plan.monthly_petition_limit is None:
        return None  # Ilimitado ou sem plano

    # Pegar uso dos últimos 7 dias
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    current_cycle = datetime.utcnow().strftime("%Y-%m")

    recent_usage = PetitionUsage.query.filter(
        PetitionUsage.user_id == user.id,
        PetitionUsage.billing_cycle == current_cycle,
        PetitionUsage.billable == True,
        PetitionUsage.generated_at >= seven_days_ago,
    ).count()

    if recent_usage == 0:
        return None  # Sem uso recente

    # Calcular média diária
    daily_average = recent_usage / 7.0

    # Uso atual no mês
    current_usage = PetitionUsage.query.filter_by(
        user_id=user.id,
        billing_cycle=current_cycle,
        billable=True,
    ).count()

    remaining = plan.plan.monthly_petition_limit - current_usage

    if remaining <= 0:
        return {
            "status": "exceeded",
            "message": "Limite já atingido",
            "days_remaining": 0,
            "daily_average": round(daily_average, 1),
        }

    # Estimar dias até atingir o limite
    days_to_limit = remaining / daily_average if daily_average > 0 else 999

    return {
        "status": "prediction",
        "days_remaining": int(days_to_limit),
        "daily_average": round(daily_average, 1),
        "estimated_date": (datetime.utcnow() + timedelta(days=days_to_limit)).strftime(
            "%d/%m/%Y"
        ),
        "message": f"Com base no uso atual ({daily_average:.1f} petições/dia), você atingirá o limite em aproximadamente {int(days_to_limit)} dias.",
    }


def get_usage_insights(user):
    """Retorna insights sobre o uso de petições."""
    current_cycle = datetime.now(timezone.utc).strftime("%Y-%m")
    last_cycle = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m")

    # Uso atual
    current_billable = PetitionUsage.query.filter_by(
        user_id=user.id,
        billing_cycle=current_cycle,
        billable=True,
    ).count()

    # Uso mês passado
    last_billable = PetitionUsage.query.filter_by(
        user_id=user.id,
        billing_cycle=last_cycle,
        billable=True,
    ).count()

    # Calcular tendência
    if last_billable > 0:
        growth_rate = ((current_billable - last_billable) / last_billable) * 100
    else:
        growth_rate = 100 if current_billable > 0 else 0

    # Dia do mês com mais uso
    peak_day = (
        PetitionUsage.query.filter_by(
            user_id=user.id, billing_cycle=current_cycle, billable=True
        )
        .with_entities(
            func.date(PetitionUsage.generated_at).label("day"),
            func.count(PetitionUsage.id).label("count"),
        )
        .group_by(func.date(PetitionUsage.generated_at))
        .order_by(func.count(PetitionUsage.id).desc())
        .first()
    )

    return {
        "current_month": current_billable,
        "last_month": last_billable,
        "growth_rate": round(growth_rate, 1),
        "trend": "up" if growth_rate > 0 else "down" if growth_rate < 0 else "stable",
        "peak_day": peak_day.day.strftime("%d/%m/%Y") if peak_day else None,
        "peak_count": peak_day.count if peak_day else 0,
    }
