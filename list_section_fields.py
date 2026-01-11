#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para listar todos os campos das seções de partes.
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


def list_section_fields(slug):
    """Lista os campos de uma seção específica."""

    section = PetitionSection.query.filter_by(slug=slug).first()

    if not section:
        print(f"[AVISO] Secao '{slug}' nao encontrada")
        return

    print(f"\n{'=' * 80}")
    print(f"[{section.id}] {section.name} ({section.slug})")
    print(f"{'=' * 80}")

    fields = section.fields_schema or []

    for i, field in enumerate(fields, 1):
        print(
            f"{i:2}. {field.get('name'):30} | tipo: {field.get('type'):12} | {field.get('label')}"
        )


def update_cpf_fields_with_link(representante_id):
    """
    Atualiza campos que parecem ser de CPF/documento para usar cpf_cnpj
    e vincular à seção de representante.
    """

    print("\n" + "=" * 80)
    print("ATUALIZANDO CAMPOS DE DOCUMENTO PARA CPF/CNPJ")
    print("=" * 80)

    # Seções de partes
    target_slugs = [
        "autor",
        "autor-peticionario",
        "reu",
        "reu-acusado",
        "terceiro-interessado",
        "testemunha",
    ]

    # Campos que devem ser convertidos (nome parcial)
    cpf_field_patterns = ["cpf", "documento", "identificacao"]

    updated = 0

    for slug in target_slugs:
        section = PetitionSection.query.filter_by(slug=slug).first()
        if not section:
            continue

        fields = section.fields_schema or []
        modified = False

        for field in fields:
            field_name = field.get("name", "").lower()
            field_type = field.get("type", "")

            # Verificar se é um campo de CPF que deveria ser cpf_cnpj
            is_cpf_field = any(pattern in field_name for pattern in cpf_field_patterns)

            if is_cpf_field and field_type in ["text", "cpf"]:
                old_type = field_type
                field["type"] = "cpf_cnpj"
                field["linked_section_id"] = representante_id
                field["linked_section_trigger"] = "cnpj"
                modified = True
                updated += 1
                print(f"\n[ATUALIZADO] {section.name}")
                print(f"  Campo: {field.get('name')}")
                print(f"  Tipo: {old_type} -> cpf_cnpj")
                print(f"  Vinculado a secao: {representante_id}")

        if modified:
            section.fields_schema = fields
            db.session.add(section)

    db.session.commit()
    print(f"\nTotal de campos atualizados: {updated}")
    return updated


def main():
    """Função principal."""

    app = create_app()

    with app.app_context():
        # Seções de partes
        slugs = [
            "autor",
            "autor-peticionario",
            "reu",
            "reu-acusado",
            "terceiro-interessado",
            "testemunha",
            "representante-legal",
        ]

        for slug in slugs:
            list_section_fields(slug)

        # Obter ID da seção de representante
        rep = PetitionSection.query.filter_by(slug="representante-legal").first()
        if rep:
            print(f"\n\nID da secao de representante: {rep.id}")

            # Perguntar se deseja atualizar
            confirm = input("\nDeseja atualizar campos de CPF para CPF/CNPJ? (s/n): ")
            if confirm.lower() == "s":
                update_cpf_fields_with_link(rep.id)

                print("\n\n" + "=" * 80)
                print("RESULTADO APOS ATUALIZACAO")
                print("=" * 80)

                for slug in slugs:
                    list_section_fields(slug)


if __name__ == "__main__":
    main()
