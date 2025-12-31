"""
Script para atualizar o roadmap com implementações recentes
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem, User


def update_roadmap_implementations():
    """Atualiza o roadmap com implementações recentes"""

    app = create_app()

    with app.app_context():
        # Buscar primeiro usuário master para created_by
        master_user = User.query.filter_by(user_type="master").first()
        if not master_user:
            print("Erro: Nenhum usuário master encontrado.")
            return

        print(f"Usando usuário master: {master_user.id} - {master_user.username}")

        # Buscar categorias
        categories = {cat.slug: cat for cat in RoadmapCategory.query.all()}

        # Verificar itens existentes para não duplicar
        existing_slugs = {item.slug for item in RoadmapItem.query.all()}

        # Novos itens a adicionar (implementações recentes)
        new_implementations = [
            # === SISTEMA DE AUDITORIA ===
            {
                "category_slug": "seguranca",
                "title": "Sistema de Logs de Auditoria Completo",
                "slug": "sistema-logs-auditoria-completo",
                "description": "Implementação completa de sistema de auditoria para rastrear ações de usuários e advogados",
                "detailed_description": "Sistema abrangente de logging de auditoria que registra todas as ações importantes no sistema, incluindo criação/edição/exclusão de dados, login/logout, geração de petições, e outras operações críticas. Inclui interface admin para visualização e filtros avançados.",
                "status": "completed",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Garantir conformidade, segurança e rastreabilidade de todas as operações no sistema",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "auditoria, logs, segurança, compliance, rastreabilidade",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=14),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=14),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === DASHBOARD FINANCEIRO ===
            {
                "category_slug": "funcionalidades",
                "title": "Dashboard Financeiro Avançado",
                "slug": "dashboard-financeiro-avancado",
                "description": "Dashboard completo para análise financeira com métricas de receita, custos e projeções",
                "detailed_description": "Implementação de dashboard financeiro com gráficos interativos, análise de tendências, métricas de LTV, CAC, margem de lucro, e relatórios exportáveis. Inclui segmentação por plano, período e tipo de usuário.",
                "status": "completed",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Melhorar análise financeira e tomada de decisões estratégicas",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "dashboard, financeiro, analytics, receita, custos",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=30),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=30),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === GESTÃO DE PLANOS E PREÇOS ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Planos e Preços Dinâmico",
                "slug": "sistema-planos-precos-dinamico",
                "description": "Sistema completo de gestão de planos de assinatura com preços dinâmicos e limites configuráveis",
                "detailed_description": "Implementação de sistema de planos flexível com configuração de limites por plano (petições, IA, armazenamento), preços dinâmicos, upgrade/downgrade automático, e integração com gateways de pagamento.",
                "status": "completed",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Otimizar monetização e oferecer flexibilidade aos usuários",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "planos, preços, monetização, limites, upgrade",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=60),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=60),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === GESTÃO DE PETIÇÕES DINÂMICAS ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Petições Dinâmicas",
                "slug": "sistema-peticao-dinamicas",
                "description": "Sistema avançado de geração de petições com formulários dinâmicos e seções configuráveis",
                "detailed_description": "Implementação completa de sistema de petições com tipos configuráveis, seções modulares, formulários dinâmicos baseados em templates, e geração automática de documentos jurídicos.",
                "status": "completed",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Revolucionar a geração de petições com flexibilidade e qualidade",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "petições, dinâmico, templates, jurídico, automação",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=90),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=90),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === SISTEMA DE IA INTEGRADO ===
            {
                "category_slug": "ia-automacao",
                "title": "Integração Completa com IA",
                "slug": "integracao-completa-ia",
                "description": "Sistema completo de IA para geração de conteúdo, análise jurídica e automação",
                "detailed_description": "Implementação de sistema de IA integrado com controle de créditos, geração de petições assistida por IA, análise de documentos, e métricas de uso. Inclui diferentes modelos de IA e controle de custos.",
                "status": "completed",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Aumentar produtividade e qualidade através da automação inteligente",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "ia, machine learning, automação, produtividade, qualidade",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=45),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=45),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === SISTEMA DE NOTIFICAÇÕES ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Notificações e Alertas",
                "slug": "sistema-notificacoes-alertas",
                "description": "Sistema completo de notificações push, email e in-app para usuários",
                "detailed_description": "Implementação de sistema de notificações abrangente com templates personalizáveis, agendamento, histórico, e integração com diferentes canais (email, push, SMS).",
                "status": "completed",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhorar engajamento e retenção através de comunicação efetiva",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "notificações, engajamento, comunicação, alertas",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=21),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=21),
                "actual_completion_date": datetime.utcnow().date(),
            },
            # === ROADMAP MANAGEMENT ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Gerenciamento de Roadmap",
                "slug": "sistema-gerenciamento-roadmap",
                "description": "Plataforma completa para gestão de roadmap de desenvolvimento com feedback dos usuários",
                "detailed_description": "Implementação de sistema de roadmap com categorias, itens priorizados, status tracking, feedback dos usuários, e interface admin completa para gestão.",
                "status": "completed",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhorar transparência e engajamento através do compartilhamento do roadmap",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "roadmap, desenvolvimento, transparência, feedback",
                "planned_start_date": datetime.utcnow().date() - timedelta(days=7),
                "planned_completion_date": datetime.utcnow().date(),
                "actual_start_date": datetime.utcnow().date() - timedelta(days=7),
                "actual_completion_date": datetime.utcnow().date(),
            },
        ]

        added_count = 0
        for item_data in new_implementations:
            slug = item_data["slug"]
            if slug in existing_slugs:
                print(f"Item {slug} já existe. Pulando.")
                continue

            category = categories.get(item_data.pop("category_slug"))
            if not category:
                print(f"Categoria {item_data['category_slug']} não encontrada. Pulando item.")
                continue

            item = RoadmapItem(
                category_id=category.id, created_by=master_user.id, **item_data
            )
            db.session.add(item)
            added_count += 1
            print(f"Adicionado: {item.title}")

        db.session.commit()
        print(f"Adicionados {added_count} novos itens implementados ao roadmap!")

        # Atualizar status de itens existentes se necessário
        # Por exemplo, marcar alguns como completed se foram implementados
        updates = [
            ("dashboard-analytics-avancado", "completed"),
            ("otimizacao-performance", "completed"),
            ("portal-cliente-avancado", "completed"),
        ]

        updated_count = 0
        for slug, new_status in updates:
            item = RoadmapItem.query.filter_by(slug=slug).first()
            if item and item.status != new_status:
                item.status = new_status
                if new_status == "completed" and not item.actual_completion_date:
                    item.actual_completion_date = datetime.utcnow().date()
                updated_count += 1
                print(f"Atualizado: {item.title} -> {new_status}")

        if updated_count > 0:
            db.session.commit()
            print(f"Atualizados {updated_count} itens existentes!")


if __name__ == "__main__":
    update_roadmap_implementations()