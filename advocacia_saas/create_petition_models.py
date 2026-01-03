#!/usr/bin/env python3
"""
Script para criar modelos de petições e vincular seções.
Os modelos são necessários para o formulário dinâmico funcionar.
"""

import sys

from app import create_app, db
from app.models import PetitionModel, PetitionModelSection, PetitionType


def create_petition_models():
    """Cria modelos para cada tipo de petição"""
    app = create_app()
    with app.app_context():
        try:
            print("📋 Iniciando criação de modelos de petições...")

            created_count = 0
            total_links = 0

            # Iterar por cada tipo de petição
            for petition_type in PetitionType.query.all():
                # Verificar se já existe modelo
                existing_model = PetitionModel.query.filter_by(
                    petition_type_id=petition_type.id, is_active=True
                ).first()

                if existing_model:
                    print(f"  ✓ Modelo já existe para '{petition_type.name}'")
                    continue

                # Gerar slug único para o modelo
                slug = f"modelo-{petition_type.slug}"

                # Criar novo modelo
                model = PetitionModel(
                    petition_type_id=petition_type.id,
                    slug=slug,
                    name=f"Modelo - {petition_type.name}",
                    description=f"Modelo padrão para {petition_type.name}",
                    template_content="",
                    is_active=True,
                )
                db.session.add(model)
                db.session.flush()  # Para obter o ID
                print(f"  ✅ Modelo criado para '{petition_type.name}'")

                # Vincular seções novas ao modelo (IDs 7-12)
                NEW_SECTION_IDS = [7, 8, 9, 10, 11, 12]  # Seções com campos
                for order, section_id in enumerate(NEW_SECTION_IDS, 1):
                    model_section = PetitionModelSection(
                        petition_model_id=model.id,
                        section_id=section_id,
                        order=order,
                        is_required=True,
                        is_expanded=(order == 1),
                        field_overrides={},
                    )
                    db.session.add(model_section)
                    total_links += 1

                created_count += 1

            db.session.commit()

            print(f"\n✨ Modelos criados com sucesso!")
            print(f"   📊 Modelos criados: {created_count}")
            print(f"   🔗 Seções vinculadas: {total_links}")

            # Verificar resultado
            print("\n📈 Verificação:")
            for pt in PetitionType.query.all():
                model = PetitionModel.query.filter_by(
                    petition_type_id=pt.id, is_active=True
                ).first()
                if model:
                    sections = PetitionModelSection.query.filter_by(
                        petition_model_id=model.id
                    ).count()
                    print(f"   {pt.name}: {sections} seções")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = create_petition_models()
    sys.exit(0 if success else 1)
