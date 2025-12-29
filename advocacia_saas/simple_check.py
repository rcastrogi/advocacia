import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.models import PetitionModel

app = create_app()
with app.app_context():
    print("=== VERIFICAÇÃO SIMPLES DOS MODELOS ===")
    models = PetitionModel.query.filter(
        PetitionModel.id.in_([27, 28, 29, 34, 35, 36])
    ).all()
    for model in models:
        sections = model.get_sections_ordered()
        print(f"Modelo {model.id}: {model.name} - {len(sections)} seções")
