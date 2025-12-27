#!/usr/bin/env python3
"""
Script para completar a migração das seções dos modelos existentes
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PetitionModel, PetitionModelSection


def complete_model_sections():
    """Completa as seções dos modelos que não têm seções"""
    app = create_app()
    with app.app_context():
        try:
            # Busca modelos sem seções
            models_without_sections = PetitionModel.query.filter(
                ~PetitionModel.model_sections.any()
            ).all()

            print(f"📊 Encontrados {len(models_without_sections)} modelos sem seções")

            completed = 0
            for model in models_without_sections:
                print(f"🔄 Completando modelo: {model.name} (ID: {model.id})")

                # Busca as seções do tipo original
                type_sections = model.petition_type.type_sections.all()
                if type_sections:
                    print(f"  📋 Adicionando {len(type_sections)} seções")

                    for type_section in type_sections:
                        # Verifica se já existe
                        existing = PetitionModelSection.query.filter_by(
                            petition_model_id=model.id,
                            section_id=type_section.section_id,
                        ).first()

                        if not existing:
                            model_section = PetitionModelSection(
                                petition_model_id=model.id,
                                section_id=type_section.section_id,
                                order=type_section.order,
                                is_required=type_section.is_required,
                                field_overrides=type_section.field_overrides or {},
                            )
                            db.session.add(model_section)

                    db.session.commit()
                    completed += 1
                    print(f"✅ Modelo {model.name} completado!")
                else:
                    print(f"⚠️  Tipo {model.petition_type.name} não tem seções")

            print(f"\n🎉 Completados {completed} modelos!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao completar seções: {str(e)}")
            return False


if __name__ == "__main__":
    success = complete_model_sections()
    sys.exit(0 if success else 1)
