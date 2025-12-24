"""
Script para popular o roadmap com itens de exemplo
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem, User


def seed_roadmap():
    """Adiciona itens de exemplo ao roadmap"""

    app = create_app()

    with app.app_context():
        # Verificar se já existem itens
        if RoadmapItem.query.count() > 0:
            print("Roadmap já possui itens. Pulando seed.")
            return

        # Buscar primeiro usuário master para created_by
        master_user = User.query.filter_by(user_type="master").first()
        if not master_user:
            print(
                "Erro: Nenhum usuário master encontrado. Crie um usuário admin primeiro."
            )
            return

        print(f"Usando usuário master: {master_user.id} - {master_user.username}")

        # Buscar categorias
        categories = {cat.slug: cat for cat in RoadmapCategory.query.all()}

        # Itens de exemplo
        roadmap_items = [
            {
                "category_slug": "funcionalidades",
                "title": "Dashboard de Analytics Avançado",
                "slug": "dashboard-analytics-avancado",
                "description": "Implementar dashboard completo com gráficos interativos e métricas em tempo real",
                "detailed_description": "Criar um dashboard moderno com ApexCharts para visualização de dados, incluindo métricas de uso, conversão, retenção e performance do sistema.",
                "status": "in_progress",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhorar a tomada de decisão com dados visuais e insights acionáveis",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "dashboard, analytics, gráficos, métricas",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=7),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=21),
            },
            {
                "category_slug": "interface",
                "title": "Modo Escuro Completo",
                "slug": "modo-escuro-completo",
                "description": "Implementar modo escuro em toda a aplicação com alternância automática",
                "detailed_description": "Adicionar suporte completo ao modo escuro usando CSS custom properties, com detecção automática de preferência do sistema e botão de alternância manual.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "medium",
                "visible_to_users": True,
                "business_value": "Melhorar a experiência do usuário e reduzir fadiga visual",
                "technical_complexity": "low",
                "user_impact": "medium",
                "tags": "interface, ux, acessibilidade, tema",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=14),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=35),
            },
            {
                "category_slug": "seguranca",
                "title": "Autenticação de Dois Fatores",
                "slug": "autenticacao-dois-fatores",
                "description": "Implementar 2FA com SMS e aplicativo autenticador",
                "detailed_description": "Adicionar autenticação de dois fatores usando TOTP (Google Authenticator) e SMS como opções, com interface de configuração no perfil do usuário.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Aumentar significativamente a segurança das contas dos usuários",
                "technical_complexity": "high",
                "user_impact": "medium",
                "tags": "segurança, 2fa, autenticação, privacidade",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=30),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=60),
            },
            {
                "category_slug": "ia-automacao",
                "title": "Assistente IA para Revisão de Petições",
                "slug": "assistente-ia-revisao-peticao",
                "description": "IA que analisa e sugere melhorias nas petições geradas",
                "detailed_description": "Implementar assistente de IA que faz análise jurídica das petições, sugere melhorias, identifica inconsistências e oferece recomendações personalizadas.",
                "status": "planned",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Revolucionar a qualidade das petições geradas e reduzir retrabalho",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "ia, machine learning, qualidade, automação",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=45),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=120),
            },
            {
                "category_slug": "mobile",
                "title": "Aplicativo Mobile Nativo",
                "slug": "aplicativo-mobile-nativo",
                "description": "Desenvolver app mobile nativo para iOS e Android",
                "detailed_description": "Criar aplicativo mobile nativo usando React Native ou Flutter, com funcionalidades principais do sistema disponíveis offline.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Expandir o alcance e melhorar a acessibilidade móvel",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "mobile, ios, android, react native",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=60),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=180),
            },
            {
                "category_slug": "performance",
                "title": "Otimização de Performance",
                "slug": "otimizacao-performance",
                "description": "Melhorar velocidade de carregamento e resposta do sistema",
                "detailed_description": "Implementar cache, otimização de queries, compressão de assets e CDN para melhorar significativamente a performance geral da plataforma.",
                "status": "in_progress",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas interno
                "internal_only": True,
                "business_value": "Melhorar satisfação do usuário e reduzir custos de infraestrutura",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "performance, cache, cdn, otimização",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=3),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=30),
            },
            {
                "category_slug": "integracao",
                "title": "Integração com Tribunais",
                "slug": "integracao-tribunais",
                "description": "API para envio direto de petições aos tribunais",
                "detailed_description": "Desenvolver integração com APIs dos tribunais para envio automático de petições, acompanhamento de processos e notificações de andamento.",
                "status": "planned",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Eliminar intermediários e agilizar todo o processo judicial",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "integração, api, tribunais, automação",
                "dependencies": "dashboard-analytics-avancado, autenticacao-dois-fatores",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=90),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=210),
            },
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Templates Personalizáveis",
                "slug": "sistema-templates-personalizaveis",
                "description": "Permitir que usuários criem e personalizem seus próprios templates",
                "detailed_description": "Implementar editor visual de templates com drag-and-drop, variáveis dinâmicas e sistema de compartilhamento entre usuários.",
                "status": "completed",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Aumentar flexibilidade e reduzir dependência de templates padrão",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "templates, personalização, editor visual",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=60),
                "planned_completion_date": datetime.utcnow().date()
                - timedelta(days=15),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=55),
                "actual_completion_date": datetime.utcnow().date() - timedelta(days=15),
            },
        ]

        for item_data in roadmap_items:
            category = categories.get(item_data.pop("category_slug"))
            if not category:
                print(
                    f"Categoria {item_data['category_slug']} não encontrada. Pulando item."
                )
                continue

            item = RoadmapItem(
                category_id=category.id, created_by=master_user.id, **item_data
            )
            db.session.add(item)

        db.session.commit()
        print(f"Adicionados {len(roadmap_items)} itens de exemplo ao roadmap!")


if __name__ == "__main__":
    seed_roadmap()
