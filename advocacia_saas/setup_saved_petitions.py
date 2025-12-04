"""
Script para criar as tabelas de petições salvas e adicionar seção de uploads.
"""

import sys

sys.path.insert(0, ".")

from app import create_app, db
from app.models import PetitionSection, PetitionType, PetitionTypeSection

app = create_app()

# Seção de uploads/provas
UPLOAD_SECTION = {
    "name": "Documentos e Provas",
    "slug": "documentos-provas",
    "description": "Upload de documentos e provas do caso",
    "icon": "fa-paperclip",
    "color": "secondary",
    "order": 100,  # Aparece no final
    "fields_schema": [
        {
            "name": "upload_info",
            "type": "info",
            "label": "Anexar Documentos",
            "description": "Você pode anexar documentos como provas, procurações, certidões e outros arquivos relevantes ao caso. Os arquivos serão salvos junto com a petição.",
            "size": "col-12",
        }
    ],
}

# Tipos de petição que devem ter seção de uploads
PETITION_TYPES_WITH_UPLOADS = [
    "acao-de-alimentos",
    "divorcio-consensual",
    "divorcio-litigioso",
    "guarda-de-filhos",
    "uniao-estavel",
    "investigacao-paternidade",
    "revisional-alimentos",
    "execucao-alimentos",
    "regulamentacao-visitas",
    "peticao-inicial-civel",
    "contestacao",
    "recurso-apelacao",
    "embargos-declaracao",
    "agravo-instrumento",
]


def create_tables():
    """Cria as tabelas no banco de dados."""
    print("Criando tabelas saved_petitions e petition_attachments...")

    with app.app_context():
        from sqlalchemy import text

        # Criar tabela saved_petitions
        try:
            db.session.execute(text("SELECT 1 FROM saved_petitions LIMIT 1"))
            print("  ✓ Tabela saved_petitions já existe")
        except:
            db.session.rollback()
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS saved_petitions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    petition_type_id INTEGER NOT NULL REFERENCES petition_types(id),
                    title VARCHAR(300),
                    process_number VARCHAR(30),
                    status VARCHAR(20) DEFAULT 'draft',
                    form_data JSONB DEFAULT '{}',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    cancelled_at TIMESTAMP
                )
            """)
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_saved_petitions_process ON saved_petitions(process_number)"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_saved_petitions_status ON saved_petitions(status)"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_saved_petitions_user ON saved_petitions(user_id)"
                )
            )
            db.session.commit()
            print("  ✓ Tabela saved_petitions criada")

        # Criar tabela petition_attachments
        try:
            db.session.execute(text("SELECT 1 FROM petition_attachments LIMIT 1"))
            print("  ✓ Tabela petition_attachments já existe")
        except:
            db.session.rollback()
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS petition_attachments (
                    id SERIAL PRIMARY KEY,
                    saved_petition_id INTEGER NOT NULL REFERENCES saved_petitions(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    stored_filename VARCHAR(255) NOT NULL,
                    file_type VARCHAR(100),
                    file_size INTEGER,
                    category VARCHAR(50) DEFAULT 'prova',
                    description VARCHAR(500),
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by_id INTEGER REFERENCES "user"(id)
                )
            """)
            )
            db.session.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_attachments_petition ON petition_attachments(saved_petition_id)"
                )
            )
            db.session.commit()
            print("  ✓ Tabela petition_attachments criada")

        print("✅ Tabelas criadas com sucesso!")


def setup_upload_section():
    """Cria a seção de uploads e vincula aos tipos de petição."""
    print("\nConfigurando seção de uploads...")

    with app.app_context():
        # Verificar se seção já existe
        section = PetitionSection.query.filter_by(slug=UPLOAD_SECTION["slug"]).first()

        if not section:
            section = PetitionSection(
                name=UPLOAD_SECTION["name"],
                slug=UPLOAD_SECTION["slug"],
                description=UPLOAD_SECTION["description"],
                icon=UPLOAD_SECTION["icon"],
                color=UPLOAD_SECTION["color"],
                order=UPLOAD_SECTION["order"],
                fields_schema=UPLOAD_SECTION["fields_schema"],
                is_active=True,
            )
            db.session.add(section)
            db.session.commit()
            print(f"  ✓ Seção '{section.name}' criada")
        else:
            print(f"  ✓ Seção '{section.name}' já existe")

        # Vincular aos tipos de petição
        for slug in PETITION_TYPES_WITH_UPLOADS:
            petition_type = PetitionType.query.filter_by(slug=slug).first()
            if petition_type:
                # Verificar se link já existe
                existing = PetitionTypeSection.query.filter_by(
                    petition_type_id=petition_type.id, section_id=section.id
                ).first()

                if not existing:
                    # Encontrar a maior ordem atual
                    max_order = (
                        db.session.query(db.func.max(PetitionTypeSection.order))
                        .filter_by(petition_type_id=petition_type.id)
                        .scalar()
                        or 0
                    )

                    link = PetitionTypeSection(
                        petition_type_id=petition_type.id,
                        section_id=section.id,
                        order=max_order + 10,  # Colocar no final
                        is_required=False,
                        is_expanded=False,  # Começa colapsada
                    )
                    db.session.add(link)
                    print(f"    + Vinculado a: {petition_type.name}")

        db.session.commit()
        print("✅ Seção de uploads configurada!")


if __name__ == "__main__":
    create_tables()
    setup_upload_section()
    print("\n🎉 Setup completo!")
