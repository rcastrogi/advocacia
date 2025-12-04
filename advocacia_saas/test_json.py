"""Testar o JSON gerado pela rota."""
from app import create_app, db
from app.models import PetitionType, PetitionTypeSection, PetitionSection
import json

app = create_app()

with app.app_context():
    petition_type = PetitionType.query.filter_by(slug='acao-de-alimentos').first()
    
    sections_config = (
        db.session.query(PetitionTypeSection)
        .filter_by(petition_type_id=petition_type.id)
        .order_by(PetitionTypeSection.order)
        .all()
    )
    
    sections = []
    for config in sections_config:
        section = db.session.get(PetitionSection, config.section_id)
        if section and section.is_active:
            sections.append({
                "section": {
                    "id": section.id,
                    "name": section.name,
                    "slug": section.slug,
                    "description": section.description,
                    "icon": section.icon,
                    "color": section.color,
                    "fields_schema": section.fields_schema or []
                },
                "is_required": config.is_required,
                "is_expanded": config.is_expanded,
                "field_overrides": config.field_overrides or {}
            })
    
    sections_json = json.dumps(sections, ensure_ascii=False)
    
    print(f"Total seções: {len(sections)}")
    print(f"\nJSON (primeiros 500 chars):\n{sections_json[:500]}...")
    print(f"\nJSON válido: {json.loads(sections_json) is not None}")
