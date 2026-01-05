"""
CLI commands para gerenciar dados
"""
import click
from datetime import datetime
from flask.cli import with_appcontext
from app import db
from app.models import RoadmapItem


@click.group()
def cli():
    """Commands"""
    pass


@cli.command()
@with_appcontext
def fill_roadmap():
    """Preenche os campos dos roadmap items"""
    
    # Item 1: Autenticação
    item1 = RoadmapItem.query.filter_by(id=1).first()
    if item1:
        item1.detailed_description = """Implementar autenticação robusta e segura para o sistema de advocacia.
Este módulo deve incluir:
- Sistema de login seguro com validação de credenciais
- Suporte a múltiplos métodos de autenticação (email/senha, SSO)
- Gestão segura de sessões e tokens JWT
- Recuperação de senha com validação de email
- Autenticação multi-fator (MFA) opcional
- Logs de acesso e tentativas de login falhadas
- Implementação de CSRF protection
- Rate limiting para tentativas de login
- Conformidade com LGPD e GDPR"""
        item1.status = "completed"
        item1.priority = "critical"
        item1.estimated_effort = "large"
        item1.visible_to_users = True
        item1.business_value = "Essencial para segurança do sistema. Sem autenticação robusta, todo o sistema fica vulnerável."
        item1.technical_complexity = "high"
        item1.user_impact = "high"
        item1.impact_score = 5
        item1.effort_score = 4
        item1.tags = "segurança, autenticação, core"
        item1.notes = "Já implementado em produção. Monitorar tentativas de acesso suspeitas."
        item1.planned_start_date = datetime(2025, 1, 1).date()
        item1.planned_completion_date = datetime(2025, 3, 15).date()
        item1.actual_start_date = datetime(2025, 1, 1).date()
        item1.actual_completion_date = datetime(2025, 3, 10).date()
        db.session.add(item1)
        click.echo("Item 1 atualizado")

    # Item 2: Gestão de Petições
    item2 = RoadmapItem.query.filter_by(id=2).first()
    if item2:
        item2.detailed_description = """Sistema completo de gestão de petições jurídicas com suporte a múltiplos tipos.
Funcionalidades:
- Criação e edição de petições com templates
- Versionamento de documentos
- Workflow de aprovação/revisão
- Assinatura digital de documentos
- Integração com serviços de protocolo
- Histórico completo de alterações
- Notificações de status
- Busca avançada e filtros
- Geração de relatórios
- Exportação em múltiplos formatos (PDF, Word, etc)"""
        item2.status = "in_progress"
        item2.priority = "critical"
        item2.estimated_effort = "xlarge"
        item2.visible_to_users = True
        item2.show_new_badge = True
        item2.business_value = "Core da aplicação. Diferencial competitivo. Aumenta produtividade dos advogados em 40-60%."
        item2.technical_complexity = "high"
        item2.user_impact = "high"
        item2.impact_score = 5
        item2.effort_score = 5
        item2.tags = "petições, workflow, core, produtividade"
        item2.notes = "MVP entregue. Expandindo com mais tipos de documentos e integrações."
        item2.planned_start_date = datetime(2025, 2, 1).date()
        item2.planned_completion_date = datetime(2025, 12, 31).date()
        item2.actual_start_date = datetime(2025, 2, 15).date()
        db.session.add(item2)
        click.echo("Item 2 atualizado")

    try:
        db.session.commit()
        click.echo("[OK] Roadmap items preenchidos com sucesso!")
    except Exception as e:
        click.echo(f"[ERRO] {str(e)}", err=True)
        db.session.rollback()


if __name__ == "__main__":
    cli()
