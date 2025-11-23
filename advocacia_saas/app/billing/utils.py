import re
from datetime import datetime
from decimal import Decimal

from flask import current_app

from app import db
from app.models import BillingPlan, PetitionType, PetitionUsage

DEFAULT_PETITION_TYPES = (
    {
        "slug": "peticao-inicial-civel",
        "name": "Petição Inicial Cível",
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

    billable = bool(petition_type.is_billable and plan.plan.plan_type == "per_usage")
    amount = Decimal("0.00")
    if billable:
        amount = petition_type.base_price or plan.plan.usage_rate or Decimal("0.00")

    usage = PetitionUsage(
        user_id=user.id,
        petition_type_id=petition_type.id,
        plan_id=plan.plan_id,
        billing_cycle=current_billing_cycle(),
        billable=billable,
        amount=amount,
    )
    db.session.add(usage)
    db.session.commit()
    return usage


def ensure_default_plan():
    """Guarantee at least one billing plan exists."""
    plan = BillingPlan.query.filter_by(slug="per-usage").first()
    if not plan:
        plan = BillingPlan(
            slug="per-usage",
            name="Pay per use",
            plan_type="per_usage",
            usage_rate=Decimal("10.00"),
            description="Cobrança por petição billable.",
        )
        db.session.add(plan)
        db.session.commit()
    return plan
