#!/usr/bin/env python3
"""
Script para verificar se os exemplos do sistema foram criados no Render
"""

import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PetitionType, PetitionSection, PetitionTemplate

def check_examples():
    """Verifica se os exemplos foram criados"""

    app = create_app()

    with app.app_context():
        print("🔍 Verificando exemplos no sistema...")

        # Verificar tipos de petição
        petition_types = PetitionType.query.all()
        print(f"📋 Tipos de petição encontrados: {len(petition_types)}")

        if petition_types:
            for pt in petition_types[:5]:  # Mostrar primeiros 5
                print(f"   - {pt.name} (categoria: {pt.category})")
            if len(petition_types) > 5:
                print(f"   ... e mais {len(petition_types) - 5} tipos")
        else:
            print("❌ Nenhum tipo de petição encontrado!")

        # Verificar seções
        sections = PetitionSection.query.all()
        print(f"📑 Seções encontradas: {len(sections)}")

        # Verificar templates
        templates = PetitionTemplate.query.all()
        print(f"📄 Templates encontrados: {len(templates)}")

        # Verificar se os tipos estão marcados como implementados
        implemented = PetitionType.query.filter_by(is_implemented=True).count()
        print(f"✅ Tipos implementados: {implemented}")

        active = PetitionType.query.filter_by(is_active=True).count()
        print(f"🟢 Tipos ativos: {active}")

if __name__ == "__main__":
    check_examples()