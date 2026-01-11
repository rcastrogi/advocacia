#!/usr/bin/env python3
import sys
sys.path.insert(0, 'F:/PROJETOS/advocacia/advocacia_saas')
from app import create_app, db
from app.models import PetitionSection

app = create_app()
with app.app_context():
    rep = PetitionSection.query.filter_by(slug='representante-legal').first()
    print(f'Secao: {rep.name}')
    print(f'Total de campos: {len(rep.fields_schema)}')
    print()
    for i, f in enumerate(rep.fields_schema, 1):
        nome = f.get('name', '')
        tipo = f.get('type', '')
        label = f.get('label', '')
        print(f'{i:2}. {nome:35} | {tipo:10} | {label}')
