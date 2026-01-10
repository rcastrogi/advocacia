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


@click.command('renew-credits')
@click.option('--dry-run', is_flag=True, help='Simula a renovação sem efetuar mudanças')
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
    
    if results['users_renewed']:
        click.echo(f"\n👥 Usuários renovados:")
        for user in results['users_renewed']:
            click.echo(f"   - {user['email']}: +{user['credits_added']} créditos (novo saldo: {user['new_balance']})")


@click.command('check-features')
@click.option('--plan', '-p', default=None, help='Slug do plano para verificar')
@with_appcontext
def check_features_cmd(plan):
    """
    Verifica as features e planos configurados no sistema.
    
    Uso:
        flask check-features
        flask check-features --plan basico
    """
    from app.models import Feature, BillingPlan
    
    click.echo("📋 Features configuradas no sistema:")
    click.echo("-" * 50)
    
    features = Feature.query.order_by(Feature.module, Feature.display_order).all()
    current_module = None
    
    for f in features:
        if f.module != current_module:
            current_module = f.module
            click.echo(f"\n📦 Módulo: {current_module.upper()}")
        
        type_icon = "🔘" if f.feature_type == "boolean" else "🔢" if f.feature_type == "limit" else "💰"
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
