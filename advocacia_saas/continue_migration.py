"""
Continuar migração dos tipos restantes
"""

import json

from app import create_app, db
from app.models import PetitionTemplate, PetitionType, PetitionTypeSection
from sqlalchemy import text

app = create_app()


def continue_migration():
    """Continua a migração dos tipos que ainda não foram migrados"""
    with app.app_context():
        try:
            # Buscar tipos dinâmicos que ainda não têm modelo
            dynamic_types = db.session.execute(
                text("""
                SELECT pt.id, pt.name, pt.slug, pt.is_active
                FROM petition_types pt
                WHERE pt.use_dynamic_form = true
                AND NOT EXISTS (
                    SELECT 1 FROM petition_models pm WHERE pm.petition_type_id = pt.id
                )
                ORDER BY pt.id
            """)
            ).fetchall()

            print(
                f"📊 Encontrados {len(dynamic_types)} tipos dinâmicos ainda não migrados"
            )

            migrated_count = 0

            for type_row in dynamic_types:
                type_id, type_name, type_slug, is_active = type_row
                print(f"\n🔄 Migrando tipo: {type_name} (ID: {type_id})")

                try:
                    # Criar modelo
                    insert_model_sql = text("""
                    INSERT INTO petition_models (name, slug, description, petition_type_id, is_active, use_dynamic_form, created_by)
                    VALUES (:name, :slug, :description, :petition_type_id, :is_active, :use_dynamic_form, 1)
                    RETURNING id
                    """)

                    model_result = db.session.execute(
                        insert_model_sql,
                        {
                            "name": f"Modelo - {type_name}",
                            "slug": f"modelo-{type_slug}",
                            "description": f"Modelo gerado automaticamente para {type_name}",
                            "petition_type_id": type_id,
                            "is_active": is_active,
                            "use_dynamic_form": True,
                        },
                    )

                    model_id = model_result.fetchone()[0]
                    print(f"  ✅ Modelo criado com ID: {model_id}")

                    # Migrar seções
                    type_sections = PetitionTypeSection.query.filter_by(
                        petition_type_id=type_id
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
                        petition_type_id=type_id
                    ).first()
                    if template:
                        update_model_sql = text("""
                        UPDATE petition_models SET default_template_id = :template_id WHERE id = :model_id
                        """)
                        db.session.execute(
                            update_model_sql,
                            {"template_id": template.id, "model_id": model_id},
                        )
                        print(f"  📄 Template vinculado: {template.name}")

                    db.session.commit()
                    migrated_count += 1
                    print(f"✅ Tipo {type_name} migrado com sucesso!")

                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Erro ao migrar tipo {type_name}: {e}")
                    continue

            print(
                f"\n🎉 Migração concluída! {migrated_count} tipos migrados nesta execução."
            )
            return True

        except Exception as e:
            print(f"❌ Erro geral na migração: {e}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    continue_migration()
