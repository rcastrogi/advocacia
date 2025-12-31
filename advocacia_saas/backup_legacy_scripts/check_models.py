from app import create_app
from app.models import PetitionModel

app = create_app()
with app.app_context():
    print("=== VERIFICAÇÃO FINAL DOS MODELOS CORRIGIDOS ===")
    models = PetitionModel.query.filter(
        PetitionModel.id.in_([27, 28, 29, 34, 35, 36])
    ).all()
    for model in models:
        print(f"ID: {model.id}, Nome: {model.name}")
        sections = model.get_sections_ordered()
        print(f"  Seções ({len(sections)}):")
        for i, section in enumerate(sections, 1):
            print(f"    {i}. {section.section.name} ({section.section.slug})")
        print()
