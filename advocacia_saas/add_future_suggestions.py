"""
Script para adicionar sugestões futuras ao roadmap
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem, User


def add_future_suggestions():
    """Adiciona sugestões futuras ao roadmap"""

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

        # Sugestões futuras - Prioridade Crítica
        critical_suggestions = [
            # === SISTEMA DE AGENDAMENTO ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Agendamento e Calendário Jurídico",
                "slug": "sistema-agendamento-calendario-juridico",
                "description": "Calendário integrado com agendamentos de audiências, prazos processuais e reuniões",
                "detailed_description": "Implementação completa de sistema de calendário jurídico com lembretes automáticos, integração com tribunais, alertas de prazos processuais, agendamento de audiências e reuniões. Inclui visualização mensal/semanal/diária, compartilhamento de calendários entre equipe e notificações push.",
                "status": "planned",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Eliminação de perda de prazos e melhor organização jurídica",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "calendário, agendamento, prazos, audiências, organização",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=30),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=120),
            },
            # === GESTÃO DE DOCUMENTOS ===
            {
                "category_slug": "funcionalidades",
                "title": "Gestão Avançada de Documentos",
                "slug": "gestao-avancada-documentos",
                "description": "Sistema completo de upload, versionamento e organização de documentos",
                "detailed_description": "Implementação de GED (Gestão Eletrônica de Documentos) com upload seguro, versionamento automático, OCR para digitalização, busca inteligente por conteúdo, compartilhamento controlado, integração com Google Drive/OneDrive e compliance LGPD.",
                "status": "planned",
                "priority": "critical",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Centralização e organização completa da documentação jurídica",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "documentos, GED, OCR, versionamento, organização",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=45),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=150),
            },
            # === COBRANÇA AUTOMÁTICA ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Cobrança Automática",
                "slug": "sistema-cobranca-automatica",
                "description": "Faturamento automático, lembretes de cobrança e integração PIX/Boleto",
                "detailed_description": "Sistema completo de cobrança automática com geração de faturas recorrentes, lembretes automáticos por email/SMS, integração com PIX, boleto bancário e cartões de crédito. Inclui dunning management, relatórios de inadimplência e dashboard financeiro.",
                "status": "planned",
                "priority": "critical",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Redução significativa de inadimplência e automação financeira",
                "technical_complexity": "high",
                "user_impact": "medium",
                "tags": "cobrança, faturamento, PIX, boleto, inadimplência",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=60),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=120),
            },
        ]

        # Sugestões futuras - Prioridade Alta
        high_suggestions = [
            # === BUSINESS INTELLIGENCE ===
            {
                "category_slug": "funcionalidades",
                "title": "Análise de Dados e Business Intelligence",
                "slug": "analise-dados-business-intelligence",
                "description": "Dashboards executivos com previsões e análise avançada de dados",
                "detailed_description": "Implementação de sistema de BI completo com dashboards executivos, análise preditiva de receita/usuários, segmentação avançada, relatórios customizáveis e machine learning para insights automáticos.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "xlarge",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Tomada de decisão baseada em dados precisos e previsões",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "BI, analytics, previsões, machine learning, dashboards",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=90),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=210),
            },
            # === COMUNICAÇÃO INTERNA ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Comunicação Interna",
                "slug": "sistema-comunicacao-interna",
                "description": "Chat e colaboração em tempo real entre membros da equipe",
                "detailed_description": "Plataforma de comunicação interna com chat em tempo real, compartilhamento de arquivos, comentários em processos, notificações push, integração com tarefas e projetos. Similar ao Slack mas focado em escritórios de advocacia.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhoria significativa na colaboração e produtividade da equipe",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "chat, comunicação, colaboração, produtividade, equipe",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=120),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=240),
            },
            # === BACKUP E RECUPERAÇÃO ===
            {
                "category_slug": "seguranca",
                "title": "Sistema de Backup e Recuperação Avançado",
                "slug": "sistema-backup-recuperacao-avancado",
                "description": "Backups automáticos, recuperação point-in-time e alta disponibilidade",
                "detailed_description": "Implementação de sistema robusto de backup com recuperação point-in-time, replicação geográfica, testes automáticos de restauração, compliance LGPD e monitoramento 24/7. Inclui SLA de disponibilidade de 99.9%.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Garantia de continuidade de negócio e proteção de dados",
                "technical_complexity": "high",
                "user_impact": "critical",
                "tags": "backup, recuperação, disponibilidade, LGPD, continuidade",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=30),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=90),
            },
            # === API PÚBLICA ===
            {
                "category_slug": "integracao",
                "title": "API Pública RESTful Completa",
                "slug": "api-publica-restful-completa",
                "description": "API completa para integração com sistemas externos",
                "detailed_description": "Desenvolvimento de API RESTful abrangente com documentação OpenAPI, autenticação OAuth2/JWT, rate limiting, webhooks, SDKs para diferentes linguagens e portal de desenvolvedores. Permite integração com sistemas jurídicos, CRMs e ferramentas de gestão.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "xlarge",
                "visible_to_users": False,  # Apenas desenvolvedores
                "internal_only": True,
                "business_value": "Criação de ecossistema de integrações e valor agregado",
                "technical_complexity": "high",
                "user_impact": "medium",
                "tags": "API, REST, integração, OAuth2, webhooks",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=150),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=300),
            },
        ]

        # Sugestões futuras - Prioridade Média
        medium_suggestions = [
            # === COMPLIANCE LGPD ===
            {
                "category_slug": "seguranca",
                "title": "Sistema de Compliance LGPD Avançado",
                "slug": "sistema-compliance-lgpd-avancado",
                "description": "Controle completo de consentimento, auditoria e relatórios de compliance",
                "detailed_description": "Implementação completa de sistema LGPD com controle granular de consentimentos, auditoria automática de acessos, relatórios de compliance, DPO tools, anonimização de dados e integração com Autoridade Nacional de Proteção de Dados.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": False,  # Apenas admin
                "internal_only": True,
                "business_value": "Conformidade legal completa e redução de riscos",
                "technical_complexity": "high",
                "user_impact": "critical",
                "tags": "LGPD, compliance, privacidade, auditoria, DPO",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=180),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=360),
            },
            # === GAMIFICAÇÃO ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Gamificação para Engajamento",
                "slug": "sistema-gamificacao-engajamento",
                "description": "Pontuação, conquistas e leaderboards para aumentar engajamento",
                "detailed_description": "Implementação de sistema de gamificação com pontos por atividades, badges por conquistas, leaderboards mensais, desafios especiais e sistema de recompensas. Motiva o uso contínuo da plataforma e competição saudável entre usuários.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "medium",
                "visible_to_users": True,
                "business_value": "Aumento significativo de engajamento e retenção de usuários",
                "technical_complexity": "low",
                "user_impact": "medium",
                "tags": "gamificação, engajamento, pontos, badges, competição",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=210),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=300),
            },
            # === PORTAL MOBILE ===
            {
                "category_slug": "mobile",
                "title": "Portal do Cliente Mobile-First",
                "slug": "portal-cliente-mobile-first",
                "description": "Otimização completa para mobile com PWA e notificações push",
                "detailed_description": "Redesign completo do portal do cliente focado em mobile, implementação de Progressive Web App (PWA), notificações push nativas, gestos touch otimizados e experiência fluida em dispositivos móveis.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhoria significativa da experiência móvel e acessibilidade",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "mobile, PWA, notificações, experiência, acessibilidade",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=240),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=360),
            },
        ]

        all_suggestions = critical_suggestions + high_suggestions + medium_suggestions

        added_count = 0
        for item_data in all_suggestions:
            slug = item_data["slug"]
            if slug in existing_slugs:
                print(f"Item {slug} já existe. Pulando.")
                continue

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
            added_count += 1
            print(f"Adicionado: {item.title} (prioridade: {item.priority})")

        db.session.commit()
        print(f"Adicionadas {added_count} novas sugestões ao roadmap!")

        # Mostrar estatísticas finais
        total_items = RoadmapItem.query.count()
        completed_items = RoadmapItem.query.filter_by(status="completed").count()
        planned_items = RoadmapItem.query.filter_by(status="planned").count()

        print("\n=== ESTATÍSTICAS FINAIS DO ROADMAP ===")
        print(f"Total de itens: {total_items}")
        print(f"Itens concluídos: {completed_items}")
        print(f"Itens planejados: {planned_items}")
        print(f"Progresso: {completed_items / total_items * 100:.1f}%")


if __name__ == "__main__":
    add_future_suggestions()
