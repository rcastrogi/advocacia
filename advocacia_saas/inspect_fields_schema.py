#!/usr/bin/env python3
"""
Script para inspecionar o conteúdo do campo fields_schema de todas as seções
"""

import json
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import PetitionSection


def inspect_fields_schema():
    """Inspeciona o conteúdo do campo fields_schema de todas as seções"""

    app = create_app()
    with app.app_context():
        print("🔍 Inspecionando campo fields_schema de todas as seções...\n")

        sections = PetitionSection.query.all()

        for section in sections:
            print(f"📋 Seção: {section.name} (ID: {section.id})")
            print(f"   Tipo: {type(section.fields_schema)}")
            print(f"   Valor: {repr(section.fields_schema)}")

            if section.fields_schema:
                if isinstance(section.fields_schema, str):
                    print("   ⚠️  É uma STRING - deveria ser objeto Python!")
                    try:
                        parsed = json.loads(section.fields_schema)
                        print(f"   ✅ JSON válido: {len(parsed)} campos")
                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON INVÁLIDO: {e}")
                        print(f"   📄 Conteúdo: {section.fields_schema[:200]}...")
                elif isinstance(section.fields_schema, (list, dict)):
                    print(
                        f"   ✅ Formato correto: {len(section.fields_schema) if isinstance(section.fields_schema, list) else 'dict'} itens"
                    )
                else:
                    print(f"   ❌ Tipo inesperado: {type(section.fields_schema)}")
            else:
                print("   ℹ️  Valor vazio/None")

            print()


if __name__ == "__main__":
    inspect_fields_schema()
