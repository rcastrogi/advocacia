"""Helper functions for configurable dashboard quick actions."""

from __future__ import annotations

from flask import url_for

from app.models import LEGACY_QUICK_ACTION_KEYS, PetitionType

BASE_ACTIONS = {
    "clients_new": {
        "label": "Novo Cliente",
        "icon": "fas fa-user-plus",
        "endpoint": "clients.new",
        "variant": "primary",
    },
    "clients_search": {
        "label": "Buscar Cliente",
        "icon": "fas fa-search",
        "endpoint": "clients.index",
        "variant": "outline-secondary",
    },
}

CATEGORY_ICONS = {
    "civel": "fas fa-file-contract",
    "familia": "fas fa-people-roof",
    "trabalhista": "fas fa-briefcase",
    "criminal": "fas fa-scale-balanced",
    "tributario": "fas fa-building-columns",
}

PETITION_ROUTE_OVERRIDES = {
    "peticao-inicial-civel": "petitions.civil_petitions",
    "peticao-familia-divorcio": "petitions.family_petitions",
}


def normalize_action_keys(keys: list[str]) -> list[str]:
    return [LEGACY_QUICK_ACTION_KEYS.get(key, key) for key in keys]


def build_quick_action_choices() -> list[tuple[str, str]]:
    choices = [(key, cfg["label"]) for key, cfg in BASE_ACTIONS.items()]
    petition_types = (
        PetitionType.query.filter(PetitionType.active.is_(True))
        .order_by(PetitionType.category, PetitionType.name)
        .all()
    )
    for petition_type in petition_types:
        category = (petition_type.category or "outros").title()
        label = f"{petition_type.name} · {category}"
        choices.append((f"petition:{petition_type.slug}", label))
    return choices


def build_dashboard_actions(keys: list[str]) -> list[dict]:
    actions: list[dict] = []
    for raw_key in keys:
        key = LEGACY_QUICK_ACTION_KEYS.get(raw_key, raw_key)
        action = _build_action_entry(key)
        if action:
            actions.append(action)
    return actions


def _build_action_entry(key: str) -> dict | None:
    if key in BASE_ACTIONS:
        data = BASE_ACTIONS[key]
        url = url_for(data["endpoint"]) if data.get("endpoint") else "#"
        return {
            "key": key,
            "label": data["label"],
            "icon": data["icon"],
            "url": url,
            "button_class": f"btn btn-{data.get('variant', 'outline-primary')} w-100",
            "disabled": False,
        }

    if key.startswith("petition:"):
        slug = key.split(":", 1)[1]
        petition_type = PetitionType.query.filter_by(slug=slug).first()
        if not petition_type:
            return None

        endpoint = PETITION_ROUTE_OVERRIDES.get(slug)
        implemented_flag = getattr(petition_type, "is_implemented", True)
        implemented = bool(implemented_flag and endpoint)
        url = url_for(endpoint) if implemented and endpoint else "#"

        category = (petition_type.category or "outros").lower()
        icon = CATEGORY_ICONS.get(category, "fas fa-file-signature")
        label = petition_type.name
        if not implemented:
            label = f"{petition_type.name} (em breve)"

        variant = "outline-primary"
        if category == "familia":
            variant = "outline-danger"
        elif category == "criminal":
            variant = "outline-dark"

        return {
            "key": key,
            "label": label,
            "icon": icon,
            "url": url,
            "button_class": f"btn btn-{variant} w-100",
            "disabled": not implemented,
        }

    return None
