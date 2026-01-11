#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script direto para atualizar campos CPF para CPF/CNPJ via SQL raw.
"""

import json
import os
import sys

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import PetitionSection
from sqlalchemy import text


def update_fields_direct():
    """Atualiza campos diretamente com flush e refresh."""

    print("=" * 80)
    print("ATUALIZACAO DIRETA DOS CAMPOS CPF/CNPJ")
    print("=" * 80)

    # Obter ID da seção de representante
    rep_section = PetitionSection.query.filter_by(slug="representante-legal").first()
    if not rep_section:
        print("[ERRO] Secao de representante nao encontrada!")
        return

    rep_id = rep_section.id
    print(f"ID da secao de representante: {rep_id}")

    # Lista de atualizações a fazer
    updates = [
        ("autor", "autor_cpf"),
        ("reu", "reu_cpf"),
        ("autor-peticionario", "documento_numero"),
        ("reu-acusado", "documento_numero"),
        ("terceiro-interessado", "documento_numero"),
    ]

    for section_slug, field_name in updates:
        print(f"\nAtualizando [{section_slug}] {field_name}...")

        # Buscar seção
        section = PetitionSection.query.filter_by(slug=section_slug).first()
        if not section:
            print(f"  [AVISO] Secao '{section_slug}' nao encontrada")
            continue

        # Obter campos
        fields = list(section.fields_schema or [])

        # Encontrar e atualizar o campo
        found = False
        for i, field in enumerate(fields):
            if field.get("name") == field_name:
                print(f"  Campo encontrado: tipo atual = {field.get('type')}")

                # Atualizar campo
                fields[i] = {
                    **field,
                    "type": "cpf_cnpj",
                    "linked_section_id": rep_id,
                    "linked_section_trigger": "cnpj",
                }
                found = True
                break

        if not found:
            print(f"  [AVISO] Campo '{field_name}' nao encontrado")
            continue

        # Salvar alteração diretamente via SQL
        fields_json = json.dumps(fields, ensure_ascii=False)

        result = db.session.execute(
            text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
            {"fields": fields_json, "id": section.id},
        )

        db.session.commit()
        print(f"  [OK] Campo atualizado e persistido")

    # Verificar resultado
    print("\n" + "=" * 80)
    print("VERIFICANDO ATUALIZACOES")
    print("=" * 80)

    # Força nova query
    db.session.expire_all()

    for section_slug, field_name in updates:
        section = PetitionSection.query.filter_by(slug=section_slug).first()
        if section:
            fields = section.fields_schema or []
            for field in fields:
                if field.get("name") == field_name:
                    tipo = field.get("type")
                    linked = field.get("linked_section_id")
                    trigger = field.get("linked_section_trigger")
                    print(f"\n[{section_slug}] {field_name}:")
                    print(f"  tipo: {tipo}")
                    print(f"  linked_section_id: {linked}")
                    print(f"  linked_section_trigger: {trigger}")


def main():
    app = create_app()

    with app.app_context():
        update_fields_direct()


if __name__ == "__main__":
    main()
