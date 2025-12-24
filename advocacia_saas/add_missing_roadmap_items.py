"""
Adicionar sugestões faltantes ao roadmap existente
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem, User


def add_missing_roadmap_items():
    """Adiciona as sugestões faltantes ao roadmap"""

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

        # Novos itens a adicionar
        new_roadmap_items = [
            # === SISTEMA DE NOTIFICAÇÕES ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Notificações Inteligentes",
                "slug": "sistema-notificacoes-inteligentes",
                "description": "Notificações contextuais e lembretes automáticos baseados no comportamento do usuário",
                "detailed_description": "Implementar sistema inteligente de notificações que aprende com o comportamento do usuário, enviando lembretes sobre prazos, sugestões de uso e alertas importantes no momento certo.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Aumentar engajamento e retenção de usuários através de comunicação personalizada",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "notificações, inteligência, engajamento, personalização",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=21),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=45),
            },
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Feedback e Avaliações",
                "slug": "sistema-feedback-avaliacoes",
                "description": "Sistema completo de avaliação de petições e coleta de feedback",
                "detailed_description": "Implementar sistema de rating para petições geradas, coleta de feedback estruturado, análise de satisfação e sugestões automáticas de melhoria baseadas no feedback.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "medium",
                "visible_to_users": True,
                "business_value": "Melhorar continuamente a qualidade das petições através do feedback dos usuários",
                "technical_complexity": "low",
                "user_impact": "medium",
                "tags": "feedback, qualidade, avaliações, melhoria contínua",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=28),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=42),
            },
            # === MARKETPLACE ===
            {
                "category_slug": "funcionalidades",
                "title": "Marketplace de Templates",
                "slug": "marketplace-templates",
                "description": "Plataforma para usuários compartilharem e venderem templates personalizados",
                "detailed_description": "Criar marketplace onde advogados podem compartilhar seus templates personalizados, vender para outros usuários, avaliar templates e ganhar comissão sobre vendas.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "xlarge",
                "visible_to_users": True,
                "business_value": "Criar nova fonte de receita e comunidade de compartilhamento",
                "technical_complexity": "high",
                "user_impact": "high",
                "tags": "marketplace, monetização, comunidade, templates",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=60),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=150),
            },
            # === GAMIFICAÇÃO ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema de Gamificação",
                "slug": "sistema-gamificacao",
                "description": "Pontos, conquistas e níveis para engajar usuários",
                "detailed_description": "Implementar sistema de pontos por uso, conquistas desbloqueáveis, níveis de experiência, leaderboards e recompensas para aumentar o engajamento e fidelização.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Aumentar retenção e engajamento através de mecânicas de jogo",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "gamificação, engajamento, pontos, conquistas",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=45),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=90),
            },
            # === PROGRAMA DE INDICAÇÃO ===
            {
                "category_slug": "funcionalidades",
                "title": "Programa de Indicação",
                "slug": "programa-indicacao",
                "description": "Sistema de referências com recompensas para usuários",
                "detailed_description": "Criar programa onde usuários ganham créditos ou benefícios ao indicar novos clientes, com tracking automático de conversões e sistema de recompensas.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "medium",
                "visible_to_users": True,
                "business_value": "Reduzir custos de aquisição de clientes através do marketing boca-a-boca",
                "technical_complexity": "low",
                "user_impact": "medium",
                "tags": "indicação, marketing, recompensas, crescimento",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=35),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=60),
            },
            # === INTEGRAÇÕES ===
            {
                "category_slug": "integracao",
                "title": "Integração com Google Drive",
                "slug": "integracao-google-drive",
                "description": "Sincronização automática com Google Drive para backup e compartilhamento",
                "detailed_description": "Permitir que usuários conectem suas contas do Google Drive para backup automático de petições, sincronização de arquivos e compartilhamento direto.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "medium",
                "visible_to_users": True,
                "business_value": "Melhorar workflow e segurança dos documentos",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "integração, google drive, backup, sincronização",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=42),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=70),
            },
            {
                "category_slug": "integracao",
                "title": "Integração com Outlook e Gmail",
                "slug": "integracao-outlook-gmail",
                "description": "Sincronização de contatos e calendário com email providers",
                "detailed_description": "Integrar com Outlook e Gmail para sincronização automática de contatos de clientes, lembretes de audiências no calendário e envio direto de petições por email.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Simplificar o workflow diário do advogado",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "integração, email, calendário, produtividade",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=50),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=85),
            },
            # === PORTAL DO CLIENTE ===
            {
                "category_slug": "funcionalidades",
                "title": "Portal do Cliente Avançado",
                "slug": "portal-cliente-avancado",
                "description": "Área dedicada para clientes acompanharem processos e comunicarem com advogados",
                "detailed_description": "Expandir o portal do cliente com chat direto, acompanhamento visual de processos, upload de documentos, agendamento de reuniões e notificações em tempo real.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhorar satisfação do cliente e reduzir comunicação por outros canais",
                "technical_complexity": "medium",
                "user_impact": "high",
                "tags": "portal cliente, comunicação, transparência, satisfação",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=55),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=100),
            },
            # === API PÚBLICA ===
            {
                "category_slug": "integracao",
                "title": "API Pública REST",
                "slug": "api-publica-rest",
                "description": "API para integrações de terceiros e automação",
                "detailed_description": "Desenvolver API REST completa para integração com outros sistemas, permitindo automação de processos, sincronização de dados e extensibilidade da plataforma.",
                "status": "planned",
                "priority": "low",
                "estimated_effort": "xlarge",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Habilitar integrações avançadas e expandir o ecossistema",
                "technical_complexity": "high",
                "user_impact": "low",
                "tags": "api, integração, automação, ecossistema",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=120),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=200),
            },
            # === WHITE-LABEL ===
            {
                "category_slug": "funcionalidades",
                "title": "Sistema White-label",
                "slug": "sistema-white-label",
                "description": "Possibilidade de customização completa da marca e identidade visual",
                "detailed_description": "Implementar sistema white-label que permite escritórios personalizarem completamente a aparência da plataforma com suas cores, logos e identidade visual.",
                "status": "planned",
                "priority": "low",
                "estimated_effort": "large",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Possibilitar vendas para grandes escritórios com identidade própria",
                "technical_complexity": "medium",
                "user_impact": "low",
                "tags": "white-label, customização, marca, identidade",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=150),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=220),
            },
            # === RELATÓRIOS AVANÇADOS ===
            {
                "category_slug": "funcionalidades",
                "title": "Relatórios Avançados e Exportação",
                "slug": "relatorios-avancados-exportacao",
                "description": "Sistema completo de relatórios com exportação em múltiplos formatos",
                "detailed_description": "Implementar geração avançada de relatórios em PDF, Excel, dashboards customizáveis e exportação automática para sistemas externos.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": True,
                "business_value": "Melhorar análise de dados e compliance com requisitos legais",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "relatórios, exportação, analytics, compliance",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=70),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=110),
            },
            # === BACKUP AUTOMÁTICO ===
            {
                "category_slug": "seguranca",
                "title": "Sistema de Backup Automático",
                "slug": "sistema-backup-automatico",
                "description": "Backups incrementais automáticos com restauração point-in-time",
                "detailed_description": "Implementar sistema robusto de backup com backups incrementais automáticos, armazenamento em múltiplas regiões e capacidade de restauração para qualquer ponto no tempo.",
                "status": "planned",
                "priority": "high",
                "estimated_effort": "large",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Garantir continuidade dos negócios e conformidade com LGPD",
                "technical_complexity": "high",
                "user_impact": "low",
                "tags": "backup, segurança, continuidade, lgpd",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=30),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=60),
            },
            # === AUDITORIA ===
            {
                "category_slug": "seguranca",
                "title": "Sistema de Auditoria Completo",
                "slug": "sistema-auditoria-completo",
                "description": "Logs detalhados de todas as ações para compliance e segurança",
                "detailed_description": "Implementar auditoria completa com logs de todas as ações dos usuários, alterações em dados sensíveis, acessos ao sistema e geração automática de relatórios de auditoria.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "medium",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Garantir compliance legal e rastreabilidade de ações",
                "technical_complexity": "medium",
                "user_impact": "low",
                "tags": "auditoria, compliance, segurança, logs",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=40),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=70),
            },
            # === INFRAESTRUTURA ===
            {
                "category_slug": "performance",
                "title": "Arquitetura de Microserviços",
                "slug": "arquitetura-microservicos",
                "description": "Migrar para arquitetura de microserviços para melhor escalabilidade",
                "detailed_description": "Refatorar a aplicação para arquitetura de microserviços, separando funcionalidades em serviços independentes para melhor manutenção, escalabilidade e resiliência.",
                "status": "planned",
                "priority": "low",
                "estimated_effort": "xlarge",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Melhorar manutenibilidade e permitir escalabilidade horizontal",
                "technical_complexity": "high",
                "user_impact": "low",
                "tags": "microserviços, arquitetura, escalabilidade, manutenção",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=180),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=300),
            },
            {
                "category_slug": "performance",
                "title": "CDN Global e Load Balancing",
                "slug": "cdn-global-load-balancing",
                "description": "Implementar CDN global e balanceamento de carga automático",
                "detailed_description": "Configurar CDN global para distribuição de conteúdo estático, implementar load balancing inteligente e otimizar para usuários em diferentes regiões geográficas.",
                "status": "planned",
                "priority": "medium",
                "estimated_effort": "large",
                "visible_to_users": False,
                "internal_only": True,
                "business_value": "Melhorar performance global e reduzir latência",
                "technical_complexity": "medium",
                "user_impact": "medium",
                "tags": "cdn, performance, global, latência",
                "planned_start_date": datetime.utcnow().date() + timedelta(days=75),
                "planned_completion_date": datetime.utcnow().date()
                + timedelta(days=105),
            },
        ]

        added_count = 0
        for item_data in new_roadmap_items:
            # Verificar se já existe
            if item_data["slug"] in existing_slugs:
                print(f"Item {item_data['slug']} já existe. Pulando.")
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

        db.session.commit()
        print(f"Adicionados {added_count} novos itens ao roadmap!")


if __name__ == "__main__":
    add_missing_roadmap_items()
