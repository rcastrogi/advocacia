#!/usr/bin/env python3
from app import create_app

app = create_app()
with app.app_context():
    from app.models import PetitionSection

    sections = PetitionSection.query.all()
    for s in sections:
        transformed = s.name.upper().replace(" ", "_").replace("/", "_")
        print(f"{s.name} -> {transformed}")
