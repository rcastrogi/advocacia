"""Helpers para formatação de logs de auditoria com badges coloridos"""

# Mapeamento de tipos de entidades para cores e ícones
ENTITY_TYPE_BADGES = {
    "user": {
        "color": "primary",
        "bg_color": "bg-primary",
        "icon": "fa-user",
        "label": "Usuário",
    },
    "client": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-briefcase",
        "label": "Cliente",
    },
    "petition": {
        "color": "success",
        "bg_color": "bg-success",
        "icon": "fa-file-alt",
        "label": "Petição",
    },
    "petition_type": {
        "color": "warning",
        "bg_color": "bg-warning",
        "icon": "fa-list",
        "label": "Tipo de Petição",
    },
    "petition_model": {
        "color": "danger",
        "bg_color": "bg-danger",
        "icon": "fa-copy",
        "label": "Modelo de Petição",
    },
    "petition_section": {
        "color": "secondary",
        "bg_color": "bg-secondary",
        "icon": "fa-layer-group",
        "label": "Seção de Petição",
    },
    "billing_plan": {
        "color": "success",
        "bg_color": "bg-success",
        "icon": "fa-credit-card",
        "label": "Plano de Cobrança",
    },
    "subscription": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-handshake",
        "label": "Assinatura",
    },
    "payment": {
        "color": "success",
        "bg_color": "bg-success",
        "icon": "fa-money-bill",
        "label": "Pagamento",
    },
    "ai_generation": {
        "color": "primary",
        "bg_color": "bg-primary",
        "icon": "fa-brain",
        "label": "Geração de IA",
    },
    "system": {
        "color": "dark",
        "bg_color": "bg-dark",
        "icon": "fa-cog",
        "label": "Sistema",
    },
}

# Mapeamento de ações para cores
ACTION_BADGES = {
    "create": {
        "color": "success",
        "bg_color": "bg-success",
        "icon": "fa-plus",
        "label": "Criar",
    },
    "update": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-edit",
        "label": "Atualizar",
    },
    "delete": {
        "color": "danger",
        "bg_color": "bg-danger",
        "icon": "fa-trash",
        "label": "Deletar",
    },
    "login": {
        "color": "success",
        "bg_color": "bg-success",
        "icon": "fa-sign-in-alt",
        "label": "Login",
    },
    "logout": {
        "color": "secondary",
        "bg_color": "bg-secondary",
        "icon": "fa-sign-out-alt",
        "label": "Logout",
    },
    "view": {
        "color": "light",
        "bg_color": "bg-light",
        "icon": "fa-eye",
        "label": "Visualizar",
    },
    "export": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-download",
        "label": "Exportar",
    },
    "import": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-upload",
        "label": "Importar",
    },
    "download": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-download",
        "label": "Download",
    },
    "upload": {
        "color": "info",
        "bg_color": "bg-info",
        "icon": "fa-upload",
        "label": "Upload",
    },
}


def get_entity_badge_config(entity_type):
    """Retorna configuração de badge para tipo de entidade"""
    return ENTITY_TYPE_BADGES.get(
        entity_type,
        {
            "color": "secondary",
            "bg_color": "bg-secondary",
            "icon": "fa-box",
            "label": entity_type.replace("_", " ").title(),
        },
    )


def get_action_badge_config(action):
    """Retorna configuração de badge para ação"""
    return ACTION_BADGES.get(
        action,
        {
            "color": "secondary",
            "bg_color": "bg-secondary",
            "icon": "fa-circle",
            "label": action.replace("_", " ").title(),
        },
    )


def format_entity_type_badge(entity_type):
    """Formata um badge HTML para tipo de entidade"""
    config = get_entity_badge_config(entity_type)
    return f"""
    <span class="badge {config["bg_color"]} d-inline-flex align-items-center gap-2" title="{config["label"]}">
        <i class="fas {config["icon"]}"></i>
        {config["label"]}
    </span>
    """


def format_action_badge(action):
    """Formata um badge HTML para ação"""
    config = get_action_badge_config(action)
    return f"""
    <span class="badge {config["bg_color"]} d-inline-flex align-items-center gap-2" title="{config["label"]}">
        <i class="fas {config["icon"]}"></i>
        {config["label"]}
    </span>
    """


def format_entity_reference(entity_type, entity_id):
    """Formata referência à entidade com estilo"""
    config = get_entity_badge_config(entity_type)
    return f"""
    <span class="badge {config["bg_color"]}" title="{config["label"]} #{entity_id}">
        <i class="fas {config["icon"]}"></i> {config["label"]} #{entity_id}
    </span>
    """


def get_entity_types_list():
    """Retorna lista de tipos de entidades disponíveis"""
    return list(ENTITY_TYPE_BADGES.keys())


def get_actions_list():
    """Retorna lista de ações disponíveis"""
    return list(ACTION_BADGES.keys())
