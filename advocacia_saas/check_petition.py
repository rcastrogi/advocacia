"""Verificar dados do tipo de petição."""

from app import create_app, db
from app.models import PetitionSection, PetitionType, PetitionTypeSection

app = create_app()

with app.app_context():
    pt = PetitionType.query.filter_by(slug="acao-de-alimentos").first()
    if pt:
        print(f"Tipo: {pt.name}")
        print(f"use_dynamic_form: {pt.use_dynamic_form}")
        print(f"is_active: {pt.is_active}")

        links = PetitionTypeSection.query.filter_by(petition_type_id=pt.id).all()
        print(f"\nLinks encontrados: {len(links)}")

        for l in links:
            section = PetitionSection.query.get(l.section_id)
            if section:
                print(f"  - {section.name} (slug: {section.slug})")
                print(f"    fields_schema: {len(section.fields_schema or [])} campos")
            else:
                print(f"  - Section ID {l.section_id} NAO ENCONTRADA")
    else:
        print("Tipo de petição não encontrado!")
