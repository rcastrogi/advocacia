"""
Migração incremental - um tipo por vez
"""

import json

from app import create_app, db
from app.models import PetitionTemplate, PetitionType, PetitionTypeSection
from sqlalchemy import text

app = create_app()


def migrate_one_type(type_id):
    """Migra um tipo específico"""
    with app.app_context():
        try:
            petition_type = PetitionType.query.get(type_id)
            if not petition_type or not petition_type.use_dynamic_form:
                print(f"Tipo {type_id} não encontrado ou não é dinâmico")
                return False

            print(f"🔄 Migrando tipo: {petition_type.name}")

            # Verificar se já existe
            existing = db.session.execute(
                text(
                    "SELECT id FROM petition_models WHERE petition_type_id = :type_id"
                ),
                {"type_id": petition_type.id},
            ).fetchone()

            if existing:
                print(f"  ⚠️ Já existe modelo para este tipo")
                return True

            # Criar modelo
            insert_model_sql = text("""
            INSERT INTO petition_models (name, slug, description, petition_type_id, is_active, use_dynamic_form, created_by)
            VALUES (:name, :slug, :description, :petition_type_id, :is_active, :use_dynamic_form, 1)
            RETURNING id
            """)

            model_result = db.session.execute(
                insert_model_sql,
                {
                    "name": f"Modelo - {petition_type.name}",
                    "slug": f"modelo-{petition_type.slug}",
                    "description": f"Modelo gerado automaticamente para {petition_type.name}",
                    "petition_type_id": petition_type.id,
                    "is_active": petition_type.is_active,
                    "use_dynamic_form": True,
                },
            )

            model_id = model_result.fetchone()[0]
            print(f"  ✅ Modelo criado com ID: {model_id}")

            # Migrar seções
            type_sections = PetitionTypeSection.query.filter_by(
                petition_type_id=petition_type.id
            ).all()
            print(f"  📋 Migrando {len(type_sections)} seções")

            for type_section in type_sections:
                insert_section_sql = text("""
                INSERT INTO petition_model_sections (petition_model_id, section_id, "order", is_required, is_expanded, field_overrides)
                VALUES (:model_id, :section_id, :order, :is_required, :is_expanded, :field_overrides)
                """)

                db.session.execute(
                    insert_section_sql,
                    {
                        "model_id": model_id,
                        "section_id": type_section.section_id,
                        "order": type_section.order,
                        "is_required": type_section.is_required,
                        "is_expanded": type_section.is_expanded,
                        "field_overrides": json.dumps(
                            type_section.field_overrides or {}
                        ),
                    },
                )

            # Vincular template
            template = PetitionTemplate.query.filter_by(
                petition_type_id=petition_type.id
            ).first()
            if template:
                update_model_sql = text("""
                UPDATE petition_models SET default_template_id = :template_id WHERE id = :model_id
                """)
                db.session.execute(
                    update_model_sql, {"template_id": template.id, "model_id": model_id}
                )
                print(f"  📄 Template vinculado: {template.name}")

            db.session.commit()
            print(f"✅ Tipo {petition_type.name} migrado com sucesso!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao migrar tipo {type_id}: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    # Migrar tipos dinâmicos um por vez
    with app.app_context():
        dynamic_types = PetitionType.query.filter_by(use_dynamic_form=True).all()
        print(f"Encontrados {len(dynamic_types)} tipos dinâmicos")

        for petition_type in dynamic_types:
            print(
                f"\n--- Migrando tipo ID {petition_type.id}: {petition_type.name} ---"
            )
            migrate_one_type(petition_type.id)
