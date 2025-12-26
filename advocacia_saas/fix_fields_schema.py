#!/usr/bin/env python3
"""
Script para verificar e corrigir dados corrompidos no campo fields_schema
das tabelas petition_sections.
"""

import json
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import PetitionSection


def fix_corrupted_fields_schema():
    """Verifica e corrige dados corrompidos no campo fields_schema"""

    app = create_app()
    with app.app_context():
        print("🔍 Verificando dados corrompidos no campo fields_schema...")

        sections = PetitionSection.query.all()
        fixed_count = 0

        for section in sections:
            try:
                # Tentar fazer parse do JSON atual
                if section.fields_schema:
                    # Se for string, tentar fazer parse
                    if isinstance(section.fields_schema, str):
                        try:
                            parsed = json.loads(section.fields_schema)
                            print(
                                f"✅ [SECTION {section.id}] Convertendo string JSON para objeto: {section.name}"
                            )
                            section.fields_schema = parsed
                            fixed_count += 1
                        except json.JSONDecodeError:
                            print(
                                f"❌ [SECTION {section.id}] JSON string inválido, resetando: {section.name}"
                            )
                            section.fields_schema = []
                            fixed_count += 1
                    # Se for lista/dict, verificar se é válido
                    elif isinstance(section.fields_schema, (list, dict)):
                        # Já está no formato correto
                        continue
                    else:
                        print(
                            f"⚠️ [SECTION {section.id}] Tipo inesperado, resetando: {section.name} ({type(section.fields_schema)})"
                        )
                        section.fields_schema = []
                        fixed_count += 1
                else:
                    # Se for None, definir como lista vazia
                    if section.fields_schema is None:
                        print(
                            f"ℹ️ [SECTION {section.id}] fields_schema é None, definindo como []: {section.name}"
                        )
                        section.fields_schema = []
                        fixed_count += 1

            except Exception as e:
                print(
                    f"❌ [SECTION {section.id}] Erro inesperado: {section.name} - {str(e)}"
                )
                section.fields_schema = []
                fixed_count += 1

        if fixed_count > 0:
            print(f"💾 Salvando {fixed_count} correções...")
            try:
                from app import db

                db.session.commit()
                print("✅ Correções salvas com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao salvar correções: {str(e)}")
                db.session.rollback()
        else:
            print("✅ Nenhum dado corrompido encontrado!")


if __name__ == "__main__":
    fix_corrupted_fields_schema()
