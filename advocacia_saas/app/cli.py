"""
Comandos CLI para o Petitio.
Use com: flask <comando>
"""

import click
from flask.cli import with_appcontext


def init_app(app):
    """Registra os comandos CLI"""
    app.cli.add_command(renew_credits_cmd)
    app.cli.add_command(check_features_cmd)
    app.cli.add_command(init_features_cmd)
    app.cli.add_command(init_office_plans_cmd)


@click.command("renew-credits")
@click.option("--dry-run", is_flag=True, help="Simula a renovação sem efetuar mudanças")
@with_appcontext
def renew_credits_cmd(dry_run):
    """
    Renova os créditos mensais de IA para usuários elegíveis.
    Executa baseado nos planos e features configuradas.

    Uso:
        flask renew-credits
        flask renew-credits --dry-run
    """
    from app.services import CreditsService

    if dry_run:
        click.echo("🔍 Modo dry-run: nenhuma alteração será feita")
        click.echo("-" * 50)

    click.echo("🔄 Iniciando renovação de créditos mensais...")

    results = CreditsService.process_monthly_renewals()

    click.echo(f"\n📊 Resultado:")
    click.echo(f"   ✅ Processados: {results['processed']}")
    click.echo(f"   ⏭️  Ignorados: {results['skipped']}")
    click.echo(f"   ❌ Erros: {results['errors']}")
    click.echo(f"   💰 Total de créditos adicionados: {results['total_credits_added']}")

    if results["users_renewed"]:
        click.echo(f"\n👥 Usuários renovados:")
        for user in results["users_renewed"]:
            click.echo(
                f"   - {user['email']}: +{user['credits_added']} créditos (novo saldo: {user['new_balance']})"
            )


@click.command("check-features")
@click.option("--plan", "-p", default=None, help="Slug do plano para verificar")
@with_appcontext
def check_features_cmd(plan):
    """
    Verifica as features e planos configurados no sistema.

    Uso:
        flask check-features
        flask check-features --plan basico
    """
    from app.models import BillingPlan, Feature

    click.echo("📋 Features configuradas no sistema:")
    click.echo("-" * 50)

    features = Feature.query.order_by(Feature.module, Feature.display_order).all()
    current_module = None

    for f in features:
        if f.module != current_module:
            current_module = f.module
            click.echo(f"\n📦 Módulo: {current_module.upper()}")

        type_icon = (
            "🔘"
            if f.feature_type == "boolean"
            else "🔢"
            if f.feature_type == "limit"
            else "💰"
        )
        click.echo(f"   {type_icon} {f.slug}: {f.name}")

    click.echo("\n" + "=" * 50)
    click.echo("💳 Planos de cobrança:")
    click.echo("-" * 50)

    if plan:
        plans = BillingPlan.query.filter_by(slug=plan).all()
    else:
        plans = BillingPlan.query.filter_by(active=True).all()

    for p in plans:
        click.echo(f"\n🏷️  {p.name} ({p.slug})")
        click.echo(f"    Tipo: {p.plan_type}")
        click.echo(f"    Valor mensal: R$ {p.monthly_fee}")

        if p.features:
            click.echo(f"    Features ({len(p.features)}):")
            for f in p.features:
                limit = p.get_feature_limit(f.slug)
                if f.feature_type == "boolean":
                    click.echo(f"      ✅ {f.slug}")
                else:
                    click.echo(f"      📊 {f.slug}: {limit}")
        else:
            click.echo("    ⚠️  Sem features configuradas")


@click.command("init-features")
@click.option("--force", is_flag=True, help="Força recriação mesmo se já existirem")
@with_appcontext
def init_features_cmd(force):
    """
    Inicializa as features/módulos padrão do sistema.

    Uso:
        flask init-features
        flask init-features --force
    """
    from app import db
    from app.models import Feature

    # Definição dos módulos/features do sistema
    DEFAULT_FEATURES = [
        # Core - Funcionalidades básicas
        {
            "slug": "clients_management",
            "name": "Gestão de Clientes",
            "module": "core",
            "feature_type": "boolean",
            "icon": "fas fa-users",
            "display_order": 1,
        },
        {
            "slug": "dashboard",
            "name": "Dashboard",
            "module": "core",
            "feature_type": "boolean",
            "icon": "fas fa-chart-pie",
            "display_order": 2,
        },
        {
            "slug": "basic_reports",
            "name": "Relatórios Básicos",
            "module": "core",
            "feature_type": "boolean",
            "icon": "fas fa-file-alt",
            "display_order": 3,
        },
        # Petições
        {
            "slug": "petitions_basic",
            "name": "Petições Básicas",
            "module": "peticoes",
            "feature_type": "boolean",
            "icon": "fas fa-file-contract",
            "display_order": 10,
        },
        {
            "slug": "petitions_templates",
            "name": "Modelos de Petição",
            "module": "peticoes",
            "feature_type": "limit",
            "default_limit": 5,
            "icon": "fas fa-copy",
            "display_order": 11,
        },
        {
            "slug": "petitions_export",
            "name": "Exportar Petições (PDF/DOCX)",
            "module": "peticoes",
            "feature_type": "boolean",
            "icon": "fas fa-download",
            "display_order": 12,
        },
        # IA
        {
            "slug": "ai_petitions",
            "name": "Petições com IA",
            "module": "ia",
            "feature_type": "credits",
            "default_limit": 10,
            "is_monthly_renewable": True,
            "icon": "fas fa-robot",
            "display_order": 20,
        },
        {
            "slug": "ai_suggestions",
            "name": "Sugestões Inteligentes",
            "module": "ia",
            "feature_type": "boolean",
            "icon": "fas fa-lightbulb",
            "display_order": 21,
        },
        {
            "slug": "ai_analysis",
            "name": "Análise de Documentos com IA",
            "module": "ia",
            "feature_type": "credits",
            "default_limit": 5,
            "is_monthly_renewable": True,
            "icon": "fas fa-brain",
            "display_order": 22,
        },
        # Prazos
        {
            "slug": "deadlines_basic",
            "name": "Controle de Prazos",
            "module": "prazos",
            "feature_type": "boolean",
            "icon": "fas fa-calendar-check",
            "display_order": 30,
        },
        {
            "slug": "deadlines_notifications",
            "name": "Notificações de Prazos",
            "module": "prazos",
            "feature_type": "boolean",
            "icon": "fas fa-bell",
            "display_order": 31,
        },
        {
            "slug": "deadlines_calendar",
            "name": "Calendário Integrado",
            "module": "prazos",
            "feature_type": "boolean",
            "icon": "fas fa-calendar-alt",
            "display_order": 32,
        },
        # Processos
        {
            "slug": "processes_management",
            "name": "Gestão de Processos",
            "module": "processos",
            "feature_type": "limit",
            "default_limit": 50,
            "icon": "fas fa-folder-open",
            "display_order": 40,
        },
        {
            "slug": "processes_timeline",
            "name": "Timeline de Processos",
            "module": "processos",
            "feature_type": "boolean",
            "icon": "fas fa-stream",
            "display_order": 41,
        },
        {
            "slug": "processes_documents",
            "name": "Documentos por Processo",
            "module": "processos",
            "feature_type": "boolean",
            "icon": "fas fa-paperclip",
            "display_order": 42,
        },
        # Documentos
        {
            "slug": "documents_storage",
            "name": "Armazenamento de Documentos",
            "module": "documentos",
            "feature_type": "limit",
            "default_limit": 500,
            "icon": "fas fa-hdd",
            "display_order": 50,
        },
        {
            "slug": "documents_ocr",
            "name": "OCR em Documentos",
            "module": "documentos",
            "feature_type": "boolean",
            "icon": "fas fa-search",
            "display_order": 51,
        },
        # Portal do Cliente
        {
            "slug": "portal_cliente",
            "name": "Portal do Cliente",
            "module": "portal",
            "feature_type": "boolean",
            "icon": "fas fa-user-tie",
            "display_order": 60,
        },
        {
            "slug": "portal_chat",
            "name": "Chat com Cliente",
            "module": "portal",
            "feature_type": "boolean",
            "icon": "fas fa-comments",
            "display_order": 61,
        },
        {
            "slug": "portal_documents",
            "name": "Compartilhar Documentos",
            "module": "portal",
            "feature_type": "boolean",
            "icon": "fas fa-share-alt",
            "display_order": 62,
        },
        # Financeiro
        {
            "slug": "financial_basic",
            "name": "Controle Financeiro",
            "module": "financeiro",
            "feature_type": "boolean",
            "icon": "fas fa-dollar-sign",
            "display_order": 70,
        },
        {
            "slug": "financial_invoices",
            "name": "Emissão de Faturas",
            "module": "financeiro",
            "feature_type": "boolean",
            "icon": "fas fa-file-invoice-dollar",
            "display_order": 71,
        },
        {
            "slug": "financial_reports",
            "name": "Relatórios Financeiros",
            "module": "financeiro",
            "feature_type": "boolean",
            "icon": "fas fa-chart-line",
            "display_order": 72,
        },
        # Avançado
        {
            "slug": "multi_users",
            "name": "Múltiplos Usuários",
            "module": "avancado",
            "feature_type": "limit",
            "default_limit": 1,
            "icon": "fas fa-user-friends",
            "display_order": 80,
        },
        {
            "slug": "api_access",
            "name": "Acesso à API",
            "module": "avancado",
            "feature_type": "boolean",
            "icon": "fas fa-plug",
            "display_order": 81,
        },
        {
            "slug": "white_label",
            "name": "White Label",
            "module": "avancado",
            "feature_type": "boolean",
            "icon": "fas fa-palette",
            "display_order": 82,
        },
        {
            "slug": "priority_support",
            "name": "Suporte Prioritário",
            "module": "avancado",
            "feature_type": "boolean",
            "icon": "fas fa-headset",
            "display_order": 83,
        },
    ]

    created = 0
    updated = 0
    skipped = 0

    click.echo("🔧 Inicializando features/módulos do sistema...")
    click.echo("-" * 50)

    for feature_data in DEFAULT_FEATURES:
        existing = Feature.query.filter_by(slug=feature_data["slug"]).first()

        if existing:
            if force:
                # Atualiza feature existente
                for key, value in feature_data.items():
                    setattr(existing, key, value)
                existing.is_active = True
                updated += 1
                click.echo(f"   🔄 Atualizado: {feature_data['slug']}")
            else:
                skipped += 1
                click.echo(f"   ⏭️  Já existe: {feature_data['slug']}")
        else:
            # Cria nova feature
            feature = Feature(**feature_data, is_active=True, default_enabled=False)
            db.session.add(feature)
            created += 1
            click.echo(f"   ✅ Criado: {feature_data['slug']}")

    db.session.commit()

    click.echo("-" * 50)
    click.echo(f"📊 Resultado:")
    click.echo(f"   ✅ Criadas: {created}")
    click.echo(f"   🔄 Atualizadas: {updated}")
    click.echo(f"   ⏭️  Ignoradas: {skipped}")
    click.echo("\n💡 Use 'flask check-features' para ver todas as features")
    click.echo("💡 Configure as features por plano em Admin > Planos > Editar")


@click.command("init-office-plans")
@click.option("--force", is_flag=True, help="Força recriação mesmo se já existirem")
@with_appcontext
def init_office_plans_cmd(force):
    """
    Cria planos de escritório de exemplo com suporte a múltiplos usuários.

    Uso:
        flask init-office-plans
        flask init-office-plans --force
    """
    from app import db
    from app.models import BillingPlan, Feature, plan_features

    # Planos de escritório
    OFFICE_PLANS = [
        {
            "slug": "escritorio_pequeno",
            "name": "Escritório Pequeno",
            "description": "Ideal para escritórios de até 3 advogados",
            "plan_type": "subscription",
            "monthly_fee": 149.00,
            "features": {
                "clients_management": True,
                "dashboard": True,
                "basic_reports": True,
                "petitions_basic": True,
                "petitions_templates": 10,
                "ai_petitions": 30,
                "deadlines_basic": True,
                "deadlines_notifications": True,
                "processes_management": 150,
                "documents_storage": 1000,
                "financial_basic": True,
                "multi_users": 3,
            },
        },
        {
            "slug": "escritorio_medio",
            "name": "Escritório Profissional",
            "description": "Para escritórios em crescimento com até 10 advogados",
            "plan_type": "subscription",
            "monthly_fee": 349.00,
            "features": {
                "clients_management": True,
                "dashboard": True,
                "basic_reports": True,
                "petitions_basic": True,
                "petitions_templates": 30,
                "petitions_export": True,
                "ai_petitions": 100,
                "ai_suggestions": True,
                "ai_analysis": 30,
                "deadlines_basic": True,
                "deadlines_notifications": True,
                "deadlines_calendar": True,
                "processes_management": 500,
                "processes_timeline": True,
                "processes_documents": True,
                "documents_storage": 5000,
                "documents_ocr": True,
                "portal_cliente": True,
                "portal_chat": True,
                "portal_documents": True,
                "financial_basic": True,
                "financial_invoices": True,
                "financial_reports": True,
                "multi_users": 10,
                "priority_support": True,
            },
        },
        {
            "slug": "escritorio_grande",
            "name": "Escritório Enterprise",
            "description": "Solução completa para grandes escritórios - até 30 advogados",
            "plan_type": "subscription",
            "monthly_fee": 699.00,
            "features": {
                "clients_management": True,
                "dashboard": True,
                "basic_reports": True,
                "petitions_basic": True,
                "petitions_templates": 100,
                "petitions_export": True,
                "ai_petitions": 500,
                "ai_suggestions": True,
                "ai_analysis": 100,
                "deadlines_basic": True,
                "deadlines_notifications": True,
                "deadlines_calendar": True,
                "processes_management": 2000,
                "processes_timeline": True,
                "processes_documents": True,
                "documents_storage": 20000,
                "documents_ocr": True,
                "portal_cliente": True,
                "portal_chat": True,
                "portal_documents": True,
                "financial_basic": True,
                "financial_invoices": True,
                "financial_reports": True,
                "multi_users": 30,
                "api_access": True,
                "white_label": True,
                "priority_support": True,
            },
        },
    ]

    created = 0
    updated = 0
    skipped = 0

    click.echo("🏢 Inicializando planos de escritório...")
    click.echo("-" * 50)

    for plan_data in OFFICE_PLANS:
        features_config = plan_data.pop("features")

        existing = BillingPlan.query.filter_by(slug=plan_data["slug"]).first()

        if existing:
            if force:
                # Atualiza plano existente
                for key, value in plan_data.items():
                    setattr(existing, key, value)
                existing.active = True

                # Remover features antigas
                db.session.execute(
                    plan_features.delete().where(plan_features.c.plan_id == existing.id)
                )
                db.session.flush()

                # Adicionar features
                for feature_slug, value in features_config.items():
                    feature = Feature.query.filter_by(slug=feature_slug).first()
                    if feature:
                        # Converter booleano para inteiro (1 = ativo)
                        if isinstance(value, bool):
                            limit_value = 1 if value else 0
                        elif isinstance(value, int):
                            limit_value = value
                        else:
                            limit_value = None
                        db.session.execute(
                            plan_features.insert().values(
                                plan_id=existing.id,
                                feature_id=feature.id,
                                limit_value=limit_value,
                            )
                        )

                updated += 1
                click.echo(f"   🔄 Atualizado: {plan_data['name']}")
            else:
                skipped += 1
                click.echo(f"   ⏭️  Já existe: {plan_data['name']}")
        else:
            # Cria novo plano
            plan = BillingPlan(**plan_data, active=True)
            db.session.add(plan)
            db.session.flush()  # Para obter o ID

            # Adicionar features ao plano
            for feature_slug, value in features_config.items():
                feature = Feature.query.filter_by(slug=feature_slug).first()
                if feature:
                    # Converter booleano para inteiro (1 = ativo)
                    if isinstance(value, bool):
                        limit_value = 1 if value else 0
                    elif isinstance(value, int):
                        limit_value = value
                    else:
                        limit_value = None
                    db.session.execute(
                        plan_features.insert().values(
                            plan_id=plan.id,
                            feature_id=feature.id,
                            limit_value=limit_value,
                        )
                    )

            created += 1
            click.echo(f"   ✅ Criado: {plan_data['name']}")

    db.session.commit()

    click.echo("-" * 50)
    click.echo(f"📊 Resultado:")
    click.echo(f"   ✅ Criados: {created}")
    click.echo(f"   🔄 Atualizados: {updated}")
    click.echo(f"   ⏭️  Ignorados: {skipped}")
    click.echo("\n💡 Use 'flask check-features' para ver os planos e features")
    click.echo("💡 Configure os planos em Admin > Planos")
