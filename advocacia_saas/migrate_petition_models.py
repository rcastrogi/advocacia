"""
Migração para separar PetitionType (classificação) de PetitionModel (configuração)
"""

import json

from app import create_app
from app.models import (
    PetitionSection,
    PetitionTemplate,
    PetitionType,
    PetitionTypeSection,
    db,
)
from sqlalchemy import text


def create_petition_model():
    """Cria o novo modelo PetitionModel no banco de dados"""

    try:
        # Verificar se tabelas já existem
        result = db.session.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'petition_models')"
            )
        )
        exists = result.fetchone()[0]

        if exists:
            print("⚠️ Tabelas já existem. Pulando criação...")
            return True

        # SQL para criar a nova tabela
        create_table_sql = text("""
        CREATE TABLE petition_models (
            id SERIAL PRIMARY KEY,
            name VARCHAR(180) NOT NULL,
            slug VARCHAR(80) UNIQUE NOT NULL,
            description TEXT,
            petition_type_id INTEGER REFERENCES petition_types(id) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Configurações do modelo
            use_dynamic_form BOOLEAN DEFAULT TRUE,
            default_template_id INTEGER REFERENCES petition_templates(id),

            -- Metadados
            created_by INTEGER REFERENCES "user"(id),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # SQL para criar tabela de relacionamento modelo-seções
        create_sections_sql = text("""
        CREATE TABLE petition_model_sections (
            id SERIAL PRIMARY KEY,
            petition_model_id INTEGER REFERENCES petition_models(id) NOT NULL,
            section_id INTEGER REFERENCES petition_sections(id) NOT NULL,
            "order" INTEGER DEFAULT 0,
            is_required BOOLEAN DEFAULT FALSE,
            is_expanded BOOLEAN DEFAULT TRUE,

            -- Sobrescrever campos específicos para este modelo
            field_overrides JSON DEFAULT '{}',

            UNIQUE(petition_model_id, section_id)
        );
        """)

        # Índices para performance
        create_indexes_sql = text("""
        CREATE INDEX idx_petition_models_petition_type_id ON petition_models(petition_type_id);
        CREATE INDEX idx_petition_models_active ON petition_models(is_active);
        CREATE INDEX idx_petition_model_sections_model_id ON petition_model_sections(petition_model_id);
        CREATE INDEX idx_petition_model_sections_order ON petition_model_sections(petition_model_id, "order");
        """)

        db.session.execute(create_table_sql)
        db.session.execute(create_sections_sql)
        db.session.execute(create_indexes_sql)
        db.session.commit()
        print(
            "✅ Tabelas petition_models e petition_model_sections criadas com sucesso!"
        )
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao criar tabelas: {e}")
        return False


def migrate_dynamic_types_to_models():
    """Migra tipos dinâmicos para o novo modelo PetitionModel"""

    try:
        # Buscar tipos dinâmicos
        dynamic_types = PetitionType.query.filter_by(use_dynamic_form=True).all()
        print(f"📊 Encontrados {len(dynamic_types)} tipos dinâmicos para migrar")

        migrated_count = 0

        for petition_type in dynamic_types:
            print(f"🔄 Migrando tipo: {petition_type.name}")

            # Verificar se já existe um modelo para este tipo
            existing_model = db.session.execute(
                text(
                    "SELECT id FROM petition_models WHERE petition_type_id = :type_id"
                ),
                {"type_id": petition_type.id},
            ).fetchone()

            if existing_model:
                print(
                    f"  ⚠️ Modelo já existe para este tipo (ID: {existing_model[0]}). Pulando..."
                )
                continue

            # Criar modelo baseado no tipo
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

            # Migrar seções do tipo para o modelo
            type_sections = PetitionTypeSection.query.filter_by(
                petition_type_id=petition_type.id
            ).all()
            print(f"  📋 Migrando {len(type_sections)} seções")

            for type_section in type_sections:
                # Verificar se já existe
                existing_section = db.session.execute(
                    text(
                        "SELECT id FROM petition_model_sections WHERE petition_model_id = :model_id AND section_id = :section_id"
                    ),
                    {"model_id": model_id, "section_id": type_section.section_id},
                ).fetchone()

                if existing_section:
                    print(
                        f"    ⚠️ Seção {type_section.section_id} já existe no modelo. Pulando..."
                    )
                    continue

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

            # Vincular template ao modelo (se existir)
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

            migrated_count += 1

        db.session.commit()
        print(f"✅ Migração concluída! {migrated_count} modelos criados.")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro na migração: {e}")
        import traceback

        traceback.print_exc()
        return False


def update_petition_type_flags():
    """Remove a flag use_dynamic_form dos tipos (não precisa mais)"""

    try:
        # Resetar todos os tipos para não usar formulário dinâmico
        # (agora será controlado pelos modelos)
        update_sql = text("""
        UPDATE petition_types SET use_dynamic_form = FALSE
        """)
        db.session.execute(update_sql)
        db.session.commit()

        print("✅ Flags use_dynamic_form resetadas nos tipos de petição.")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao atualizar flags: {e}")
        return False


def main():
    """Executa a migração completa"""
    app = create_app()

    with app.app_context():
        print("🚀 Iniciando migração para separar PetitionType de PetitionModel...")

        # 1. Criar novas tabelas
        if not create_petition_model():
            return False

        # 2. Migrar dados
        if not migrate_dynamic_types_to_models():
            return False

        # 3. Limpar flags antigas
        if not update_petition_type_flags():
            return False

        print("🎉 Migração concluída com sucesso!")
        print("\n📋 Resumo:")
        print("- Criadas tabelas petition_models e petition_model_sections")
        print("- Migrados tipos dinâmicos para modelos")
        print("- Vinculados templates aos modelos")
        print("- Flags use_dynamic_form limpas")

        return True


if __name__ == "__main__":
    main()
