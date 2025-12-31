#!/usr/bin/env python3
"""
Script final para demonstrar a separação bem-sucedida entre PetitionType e PetitionModel
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PetitionModel, PetitionModelSection, PetitionType


def demonstrate_separation():
    """Demonstra a separação bem-sucedida entre tipos e modelos"""
    app = create_app()
    with app.app_context():
        print("🎯 DEMONSTRAÇÃO: Separação entre PetitionType e PetitionModel")
        print("=" * 70)

        # Estatísticas gerais
        total_types = PetitionType.query.count()
        dynamic_types = PetitionType.query.filter(
            PetitionType.type_sections.any()
        ).count()
        total_models = PetitionModel.query.count()
        total_model_sections = PetitionModelSection.query.count()

        print(f"📊 ESTATÍSTICAS GERAIS:")
        print(f"   • Total de PetitionTypes: {total_types}")
        print(f"   • Tipos dinâmicos (com seções): {dynamic_types}")
        print(f"   • PetitionModels criados: {total_models}")
        print(f"   • PetitionModelSections criadas: {total_model_sections}")
        print()

        # Demonstra a separação
        print("🔄 SEPARAÇÃO CONCLUÍDA:")
        print("   ✅ PetitionType = Classificação pura (ex: 'Ação de Cobrança')")
        print("   ✅ PetitionModel = Configuração completa (seções, ordem, overrides)")
        print()

        # Exemplos de modelos criados
        print("📋 EXEMPLOS DE MODELOS CRIADOS:")
        models = PetitionModel.query.limit(5).all()
        for model in models:
            section_count = model.model_sections.count()
            print(f"   • {model.name}")
            print(f"     └─ Tipo: {model.petition_type.name}")
            print(f"     └─ Seções: {section_count}")
            print(f"     └─ Slug: {model.slug}")
        print()

        # Verifica integridade
        print("✅ VERIFICAÇÃO DE INTEGRIDADE:")
        models_without_sections = PetitionModel.query.filter(
            ~PetitionModel.model_sections.any()
        ).count()
        print(f"   • Modelos sem seções: {models_without_sections} (deve ser 0)")

        orphaned_sections = (
            db.session.query(PetitionModelSection)
            .filter(~PetitionModelSection.petition_model.has())
            .count()
        )
        print(f"   • Seções órfãs: {orphaned_sections} (deve ser 0)")

        # Verifica se todos os tipos dinâmicos foram migrados
        migrated_types = (
            PetitionModel.query.with_entities(PetitionModel.petition_type_id)
            .distinct()
            .count()
        )
        print(f"   • Tipos dinâmicos migrados: {migrated_types}/{dynamic_types}")
        print()

        if (
            models_without_sections == 0
            and orphaned_sections == 0
            and migrated_types == dynamic_types
        ):
            print("🎉 MIGRAÇÃO BEM-SUCEDIDA!")
            print("   A separação entre classificação e configuração foi completada.")
            return True
        else:
            print("⚠️  MIGRAÇÃO INCOMPLETA")
            print("   Ainda há trabalho pendente.")
            return False


if __name__ == "__main__":
    success = demonstrate_separation()
    sys.exit(0 if success else 1)
