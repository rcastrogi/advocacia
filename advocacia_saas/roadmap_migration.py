"""
Criação das tabelas para o sistema de Roadmap
"""

from app import create_app, db
from app.models import RoadmapCategory, RoadmapItem


def create_roadmap_tables():
    """Cria as tabelas do roadmap e insere dados padrão"""

    app = create_app()

    with app.app_context():
        # Criar tabelas
        print("Criando tabelas do roadmap...")
        db.create_all()

        # Verificar se já existem categorias
        if RoadmapCategory.query.count() == 0:
            print("Inserindo categorias padrão...")

            categories_data = [
                {
                    "name": "Funcionalidades",
                    "slug": "funcionalidades",
                    "description": "Novas funcionalidades e melhorias",
                    "icon": "fa-lightbulb",
                    "color": "primary",
                    "order": 1,
                },
                {
                    "name": "Interface",
                    "slug": "interface",
                    "description": "Melhorias na interface do usuário",
                    "icon": "fa-palette",
                    "color": "info",
                    "order": 2,
                },
                {
                    "name": "Performance",
                    "slug": "performance",
                    "description": "Otimização de performance e velocidade",
                    "icon": "fa-tachometer-alt",
                    "color": "success",
                    "order": 3,
                },
                {
                    "name": "Segurança",
                    "slug": "seguranca",
                    "description": "Melhorias de segurança e privacidade",
                    "icon": "fa-shield-alt",
                    "color": "danger",
                    "order": 4,
                },
                {
                    "name": "Integração",
                    "slug": "integracao",
                    "description": "Integrações com sistemas externos",
                    "icon": "fa-plug",
                    "color": "warning",
                    "order": 5,
                },
                {
                    "name": "Mobile",
                    "slug": "mobile",
                    "description": "Aplicativos e funcionalidades móveis",
                    "icon": "fa-mobile-alt",
                    "color": "secondary",
                    "order": 6,
                },
                {
                    "name": "IA e Automação",
                    "slug": "ia-automacao",
                    "description": "Recursos de inteligência artificial",
                    "icon": "fa-robot",
                    "color": "dark",
                    "order": 7,
                },
                {
                    "name": "Outros",
                    "slug": "outros",
                    "description": "Outras melhorias e correções",
                    "icon": "fa-cog",
                    "color": "muted",
                    "order": 8,
                },
            ]

            for cat_data in categories_data:
                category = RoadmapCategory(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                    icon=cat_data["icon"],
                    color=cat_data["color"],
                    order=cat_data["order"],
                    is_active=True,
                )
                db.session.add(category)

            db.session.commit()
            print("Categorias criadas com sucesso!")

        print("Migração do roadmap concluída!")


if __name__ == "__main__":
    create_roadmap_tables()
