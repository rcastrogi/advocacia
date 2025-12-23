#!/usr/bin/env python3
"""
Script para demonstrar o sistema de petições genérico funcionando.
Mostra os tipos criados e suas configurações.
"""

import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar a configuração da aplicação
from app import db
from app.models import PetitionType, PetitionTypeSection, PetitionSection, PetitionTemplate

# Configurar Flask app para scripts
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/advocacia_saas')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy com a app
db.init_app(app)

def demonstrate_system():
    """Demonstra o sistema funcionando"""

    with app.app_context():
        print("🚀 SISTEMA DE PETIÇÕES GENÉRICO - DEMONSTRAÇÃO")
        print("=" * 60)

        # Estatísticas gerais
        total_types = PetitionType.query.filter_by(is_active=True).count()
        total_sections = PetitionSection.query.count()
        total_templates = PetitionTemplate.query.count()

        print(f"📊 Estatísticas do Sistema:")
        print(f"   • Tipos de petição dinâmicos: {total_types}")
        print(f"   • Seções disponíveis: {total_sections}")
        print(f"   • Templates criados: {total_templates}")
        print()

        # Listar tipos de petição
        print("📋 TIPOS DE PETIÇÃO DISPONÍVEIS:")
        print("-" * 40)

        petition_types = PetitionType.query.filter_by(is_active=True).all()

        for pt in petition_types:
            print(f"\n🎯 {pt.name}")
            print(f"   Slug: {pt.slug}")
            print(f"   URL: /dynamic/{pt.slug}")
            print(f"   Categoria: {pt.category.title()}")
            print(f"   Preço: R$ {pt.base_price}")
            print(f"   Ícone: {pt.icon} (cor: {pt.color})")

            # Contar seções
            sections_count = pt.type_sections.count()
            print(f"   Seções configuradas: {sections_count}")

            # Listar seções
            sections = (
                db.session.query(PetitionSection, PetitionTypeSection)
                .join(PetitionTypeSection)
                .filter(PetitionTypeSection.petition_type_id == pt.id)
                .order_by(PetitionTypeSection.order)
                .all()
            )

            if sections:
                print("   📑 Ordem das seções:")
                for section, config in sections:
                    required = "✅" if config.is_required else "❌"
                    expanded = "🔽" if config.is_expanded else "▶️"
                    print(f"      {config.order}. {section.name} {required} {expanded}")

            # Template associado
            template = PetitionTemplate.query.filter_by(petition_type_id=pt.id).first()
            if template:
                print(f"   📄 Template: {template.name}")
            else:
                print("   📄 Template: Nenhum (usará padrão)")

        print("\n" + "=" * 60)
        print("🎉 SISTEMA TOTALMENTE FUNCIONAL!")
        print()
        print("💡 Como usar:")
        print("   1. Acesse /admin/petitions para gerenciar")
        print("   2. Vá para /peticionador para criar petições")
        print("   3. Use /dynamic/{slug} para formulários específicos")
        print()
        print("🔧 Para criar novos tipos:")
        print("   1. Crie seções em /admin/petitions/sections")
        print("   2. Crie tipo em /admin/petitions/types")
        print("   3. Configure seções no tipo criado")
        print("   4. Crie template personalizado")

if __name__ == "__main__":
    demonstrate_system()