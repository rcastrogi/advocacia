import re
from datetime import datetime, timedelta
from decimal import Decimal

from flask import current_app

from app import db
from app.models import BillingPlan, Notification, PetitionType, PetitionUsage

DEFAULT_PETITION_TYPES = (
    {
        "slug": "peticao-inicial-civel",
        "name": "Petição Cível",
        "category": "civel",
        "description": "Modelo genérico para demandas cíveis de baixa complexidade.",
        "base_price": Decimal("20.00"),
    },
    {
        "slug": "acao-de-cobranca",
        "name": "Ação de Cobrança",
        "category": "civel",
        "description": "Cobrança de valores decorrentes de contratos ou títulos.",
        "base_price": Decimal("35.00"),
    },
    {
        "slug": "acao-de-alimentos",
        "name": "Ação de Alimentos",
        "category": "familia",
        "description": "Pedidos de alimentos provisórios ou definitivos.",
        "base_price": Decimal("40.00"),
    },
    {
        "slug": "guarda-e-regulacao-de-visitas",
        "name": "Guarda e Regulamentação de Visitas",
        "category": "familia",
        "description": "Discussões sobre guarda compartilhada, unilateral e convívio.",
        "base_price": Decimal("38.00"),
    },
    {
        "slug": "divorcio-consensual",
        "name": "Divórcio Consensual",
        "category": "familia",
        "description": "Divórcio amigável com partilha básica.",
        "base_price": Decimal("32.00"),
    },
    {
        "slug": "pedido-de-habeas-corpus",
        "name": "Pedido de Habeas Corpus",
        "category": "criminal",
        "description": "Liberdade de locomoção em caso de ameaça ou coação ilegal.",
        "base_price": Decimal("45.00"),
    },
    {
        "slug": "defesa-criminal",
        "name": "Defesa Criminal",
        "category": "criminal",
        "description": "Peças de defesa prévia, alegações finais e memoriais.",
        "base_price": Decimal("37.00"),
    },
    {
        "slug": "reclamacao-trabalhista",
        "name": "Reclamação Trabalhista",
        "category": "trabalhista",
        "description": "Pedidos de horas extras, verbas rescisórias e equiparação.",
        "base_price": Decimal("42.00"),
    },
    {
        "slug": "defesa-trabalhista",
        "name": "Defesa Trabalhista",
        "category": "trabalhista",
        "description": "Contestação a reclamatórias com tese patronal.",
        "base_price": Decimal("34.00"),
    },
    {
        "slug": "mandado-de-seguranca",
        "name": "Mandado de Segurança",
        "category": "tributario",
        "description": "Controle de legalidade de ato de autoridade.",
        "base_price": Decimal("50.00"),
    },
    {
        "slug": "execucao-fiscal",
        "name": "Execução Fiscal",
        "category": "tributario",
        "description": "Peças iniciais ou defesas em execuções fiscais.",
        "base_price": Decimal("39.00"),
    },
    {
        "slug": "peticao-personalizada",
        "name": "Petição Personalizada",
        "category": "outros",
        "description": "Modelo livre para demandas específicas do escritório.",
        "is_billable": False,
        "base_price": Decimal("0.00"),
    },
)


class BillingAccessError(Exception):
    """Raised when user cannot access billing-protected resources."""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def ensure_petition_type(defaults: dict) -> PetitionType:
    slug = defaults["slug"]
    petition_type = PetitionType.query.filter_by(slug=slug).first()
    if petition_type:
        return petition_type

    petition_type = PetitionType(
        slug=slug,
        name=defaults.get("name", slug.replace("-", " ").title()),
        description=defaults.get("description"),
        category=defaults.get("category", "civel"),
        is_billable=defaults.get("is_billable", True),
        base_price=defaults.get("base_price", Decimal("0.00")),
        active=True,
    )
    db.session.add(petition_type)
    db.session.commit()
    current_app.logger.info("Criado tipo de petição padrão: %s", slug)
    return petition_type


def ensure_default_petition_types() -> list[PetitionType]:
    """Seed common petition types used across the platform."""
    created = []
    for defaults in DEFAULT_PETITION_TYPES:
        petition_type = ensure_petition_type(defaults)
        created.append(petition_type)
    return created


def current_billing_cycle() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def record_petition_usage(user, petition_type: PetitionType) -> PetitionUsage:
    plan = user.get_active_plan()
    if not plan or plan.status != "active":
        raise BillingAccessError("Sua assinatura não está ativa.")

    if user.is_delinquent:
        raise BillingAccessError("Assinatura inadimplente.")

    # Determinar se esta petição será billable
    will_be_billable = bool(
        petition_type.is_billable and plan.plan.plan_type == "per_usage"
    )

    # Verificar limites APENAS para petições billable em planos mensais
    if (
        petition_type.is_billable
        and plan.plan.plan_type == "monthly"
        and plan.plan.monthly_petition_limit is not None
    ):
        # Contar APENAS petições billable do ciclo atual
        current_cycle = current_billing_cycle()
        used_this_month = PetitionUsage.query.filter_by(
            user_id=user.id,
            billing_cycle=current_cycle,
            billable=True,  # Conta apenas petições que têm valor
        ).count()

        if used_this_month >= plan.plan.monthly_petition_limit:
            raise BillingAccessError(
                f"Você atingiu o limite de {plan.plan.monthly_petition_limit} petições billable para o plano {plan.plan.name}. "
                "Aguarde o próximo ciclo ou faça upgrade para um plano com mais petições."
            )

        # Criar notificação quando atingir 80% do limite
        if used_this_month == int(plan.plan.monthly_petition_limit * 0.8):
            _create_limit_warning_notification(user, plan.plan, used_this_month)

    # Calcular valor apenas se for billable no plano per_usage
    amount = Decimal("0.00")
    if will_be_billable:
        amount = petition_type.base_price or Decimal("0.00")

    usage = PetitionUsage(
        user_id=user.id,
        petition_type_id=petition_type.id,
        plan_id=plan.plan_id,
        billing_cycle=current_billing_cycle(),
        billable=will_be_billable,
        amount=amount,
    )
    db.session.add(usage)
    db.session.commit()
    return usage


def get_user_petition_usage(user) -> dict:
    """Retorna estatísticas de uso de petições do usuário no ciclo atual."""
    plan = user.get_active_plan()
    if not plan:
        return {
            "plan_name": "Sem plano",
            "plan_type": None,
            "limit": None,
            "used": 0,
            "remaining": None,
            "percentage_used": 0,
            "is_unlimited": True,
        }

    current_cycle = current_billing_cycle()

    # Contar APENAS petições billable (as que têm valor)
    billable_used = PetitionUsage.query.filter_by(
        user_id=user.id,
        billing_cycle=current_cycle,
        billable=True,
    ).count()

    # Contar total (incluindo gratuitas) para informação
    total_used = PetitionUsage.query.filter_by(
        user_id=user.id,
        billing_cycle=current_cycle,
    ).count()

    limit = plan.plan.monthly_petition_limit
    is_unlimited = limit is None

    return {
        "plan_name": plan.plan.name,
        "plan_type": plan.plan.plan_type,
        "limit": limit,
        "used": billable_used,  # Apenas billable contam para o limite
        "total_used": total_used,  # Total incluindo gratuitas
        "free_used": total_used - billable_used,  # Petições gratuitas
        "remaining": None if is_unlimited else max(0, limit - billable_used),
        "percentage_used": 0
        if is_unlimited
        else min(100, int((billable_used / limit) * 100)),
        "is_unlimited": is_unlimited,
        "is_near_limit": False if is_unlimited else (billable_used >= limit * 0.8),
        "is_over_limit": False if is_unlimited else (billable_used >= limit),
    }


def ensure_default_plan():
    """Guarantee at least one billing plan exists."""
    plan = BillingPlan.query.filter_by(slug="per-usage").first()
    if not plan:
        plan = BillingPlan(
            slug="per-usage",
            name="Pay per use",
            plan_type="per_usage",
            monthly_fee=Decimal("0.00"),
            description="Cobrança por petição billable.",
        )
        db.session.add(plan)
        db.session.commit()
    return plan


def _create_limit_warning_notification(user, plan, used_count):
    """
    Cria notificação quando usuário atinge 80% do limite mensal.
    Verifica se já existe notificação similar neste ciclo para evitar duplicatas.
    """
    current_cycle = current_billing_cycle()

    # Verificar se já existe notificação de limite neste ciclo
    existing = (
        Notification.query.filter_by(
            user_id=user.id,
            type="ai_limit",
        )
        .filter(
            Notification.created_at
            >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        )
        .first()
    )

    if existing:
        return  # Já notificou neste ciclo

    limit = plan.monthly_petition_limit
    percentage = int((used_count / limit) * 100)
    remaining = limit - used_count

    notification = Notification(
        user_id=user.id,
        type="ai_limit",
        title="⚠️ Limite de Petições Próximo",
        message=f"Você já utilizou {used_count} de {limit} petições ({percentage}%). Restam apenas {remaining} petições neste mês. Considere fazer upgrade para continuar gerando petições sem interrupções.",
        link="/payments/plans",
        read=False,
    )

    db.session.add(notification)
    db.session.commit()


def get_unread_notifications(user):
    """Retorna todas as notificações não lidas do usuário."""
    return (
        Notification.query.filter_by(user_id=user.id, read=False)
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_notification_as_read(notification_id, user):
    """Marca uma notificação como lida."""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=user.id
    ).first()

    if notification:
        notification.read = True
        notification.read_at = datetime.utcnow()
        db.session.commit()
        return True
    return False


def create_notification(user, notification_type, title, message, link=None):
    """
    Função genérica para criar notificações.

    Args:
        user: Objeto User
        notification_type: String com tipo ('ai_limit', 'payment_due', 'credit_low', 'system', etc.)
        title: Título da notificação
        message: Mensagem completa
        link: URL opcional para ação relacionada
    """
    notification = Notification(
        user_id=user.id,
        type=notification_type,
        title=title,
        message=message,
        link=link,
        read=False,
    )

    db.session.add(notification)
    db.session.commit()
    return notification


def create_credit_low_notification(user, current_balance, threshold=10):
    """Cria notificação quando créditos IA estão baixos."""
    # Verificar se já existe notificação similar recente (últimas 24h)
    from datetime import timedelta

    recent = (
        Notification.query.filter_by(user_id=user.id, type="credit_low")
        .filter(Notification.created_at >= datetime.utcnow() - timedelta(hours=24))
        .first()
    )

    if recent:
        return None  # Já notificou recentemente

    return create_notification(
        user=user,
        notification_type="credit_low",
        title="⚠️ Créditos IA Baixos",
        message=f"Você tem apenas {current_balance} créditos IA restantes. Recarregue seus créditos para continuar usando a geração de petições com IA.",
        link="/ai/credits",
    )


def create_subscription_expiring_notification(user, days_until_expiry):
    """Cria notificação quando assinatura está próxima de expirar."""
    # Verificar se já notificou sobre essa expiração
    recent = (
        Notification.query.filter_by(user_id=user.id, type="payment_due")
        .filter(Notification.created_at >= datetime.utcnow() - timedelta(days=3))
        .first()
    )

    if recent:
        return None

    return create_notification(
        user=user,
        notification_type="payment_due",
        title="🔔 Assinatura Expirando",
        message=f"Sua assinatura expira em {days_until_expiry} dias. Mantenha seu plano ativo para continuar usando todos os recursos do Petitio.",
        link="/billing/portal",
    )


def create_petition_ready_notification(user, petition_title, petition_id):
    """Cria notificação quando petição IA está pronta."""
    return create_notification(
        user=user,
        notification_type="petition_ready",
        title="✅ Petição Pronta",
        message=f'A petição "{petition_title}" foi gerada com sucesso e está pronta para download.',
        link=f"/petitions/saved/{petition_id}",
    )
