#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para analisar e atualizar campos CPF para CPF/CNPJ.
Mostra detalhadamente todos os campos de CPF e permite atualizar.
"""

import json
import os
import sys
from datetime import datetime, timezone

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import PetitionSection


def analyze_cpf_fields():
    """Analisa todos os campos de CPF/CNPJ existentes."""

    print("\n" + "=" * 80)
    print("ANALISE DETALHADA DE CAMPOS CPF/CNPJ")
    print("=" * 80)

    sections = PetitionSection.query.order_by(PetitionSection.id).all()

    all_cpf_fields = []

    for section in sections:
        fields = section.fields_schema or []

        for field in fields:
            field_type = field.get("type", "text")
            field_name = field.get("name", "")

            if field_type in ["cpf", "cnpj", "cpf_cnpj"]:
                info = {
                    "section_id": section.id,
                    "section_name": section.name,
                    "section_slug": section.slug,
                    "field_name": field_name,
                    "field_label": field.get("label", ""),
                    "field_type": field_type,
                    "linked_section_id": field.get("linked_section_id"),
                    "linked_section_trigger": field.get("linked_section_trigger"),
                }
                all_cpf_fields.append(info)

                print(f"\n[Secao {section.id}] {section.name}")
                print(f"  Campo: {field_name}")
                print(f"  Label: {field.get('label', '-')}")
                print(f"  Tipo: {field_type}")
                print(
                    f"  Linked Section ID: {field.get('linked_section_id', 'Nao configurado')}"
                )
                print(
                    f"  Linked Trigger: {field.get('linked_section_trigger', 'Nao configurado')}"
                )

    print("\n" + "-" * 80)
    print(f"Total de campos CPF/CNPJ encontrados: {len(all_cpf_fields)}")

    # Agrupar por tipo
    by_type = {}
    for f in all_cpf_fields:
        t = f["field_type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(f)

    print("\nPor tipo:")
    for t, fields in by_type.items():
        print(f"  - {t}: {len(fields)} campo(s)")

    return all_cpf_fields


def show_representante_section():
    """Mostra os campos da seção de representante legal."""

    print("\n" + "=" * 80)
    print("SECAO DE REPRESENTANTE LEGAL")
    print("=" * 80)

    section = PetitionSection.query.filter_by(slug="representante-legal").first()

    if not section:
        print("[AVISO] Secao 'representante-legal' nao encontrada!")
        return None

    print(f"\nID: {section.id}")
    print(f"Nome: {section.name}")
    print(f"Slug: {section.slug}")
    print(f"Descricao: {section.description}")
    print(f"Ativa: {section.is_active}")
    print(f"\nCampos ({len(section.fields_schema or [])} campos):")

    for i, field in enumerate(section.fields_schema or [], 1):
        print(
            f"  {i}. {field.get('name')} ({field.get('type')}) - {field.get('label')}"
        )

    return section


def update_sections_cpf_to_cpf_cnpj(representante_section_id):
    """
    Atualiza campos CPF para CPF/CNPJ nas seções de autor/réu e similares.
    """

    print("\n" + "=" * 80)
    print("ATUALIZANDO CAMPOS CPF PARA CPF/CNPJ")
    print("=" * 80)

    # Seções que devem ter campos convertidos para cpf_cnpj
    # (partes que podem ser pessoa física ou jurídica)
    target_sections = [
        "autor",
        "autor-peticionario",
        "reu",
        "reu-acusado",
        "terceiro-interessado",
        "conjuge1",
        "conjuge2",
        "testemunha",
    ]

    # Campos que devem ser convertidos
    target_field_names = ["cpf", "autor_cpf", "reu_cpf", "cpf_cnpj", "documento"]

    updated_count = 0

    for slug in target_sections:
        section = PetitionSection.query.filter_by(slug=slug).first()
        if not section:
            print(f"\n[AVISO] Secao '{slug}' nao encontrada")
            continue

        fields = section.fields_schema or []
        if not fields:
            continue

        modified = False
        new_fields = []

        for field in fields:
            field_type = field.get("type", "text")
            field_name = field.get("name", "")

            # Converter campo CPF para CPF/CNPJ
            if field_type == "cpf" and any(
                kw in field_name.lower() for kw in ["cpf", "documento"]
            ):
                field["type"] = "cpf_cnpj"
                field["linked_section_id"] = representante_section_id
                field["linked_section_trigger"] = "cnpj"
                modified = True
                updated_count += 1
                print(f"\n[ATUALIZADO] Secao '{section.name}'")
                print(f"  Campo '{field_name}' convertido de 'cpf' para 'cpf_cnpj'")
                print(
                    f"  Vinculado a secao de representante (ID: {representante_section_id})"
                )

            new_fields.append(field)

        if modified:
            section.fields_schema = new_fields
            db.session.add(section)

    db.session.commit()
    print(f"\nTotal de campos atualizados: {updated_count}")
    return updated_count


def update_representante_section_fields():
    """Atualiza os campos da seção de representante para ter os campos necessários."""

    print("\n" + "=" * 80)
    print("ATUALIZANDO CAMPOS DA SECAO DE REPRESENTANTE")
    print("=" * 80)

    section = PetitionSection.query.filter_by(slug="representante-legal").first()

    if not section:
        print("[ERRO] Secao 'representante-legal' nao encontrada!")
        return False

    # Novos campos do representante (pessoa física)
    new_fields = [
        {
            "name": "representante_nome",
            "label": "Nome Completo do Representante",
            "type": "text",
            "required": True,
            "size": "col-md-6",
            "placeholder": "Nome completo do representante legal",
        },
        {
            "name": "representante_cpf",
            "label": "CPF do Representante",
            "type": "cpf",
            "required": True,
            "size": "col-md-6",
            "placeholder": "000.000.000-00",
        },
        {
            "name": "representante_rg",
            "label": "RG do Representante",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "00.000.000-0",
        },
        {
            "name": "representante_nacionalidade",
            "label": "Nacionalidade",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Brasileiro(a)",
        },
        {
            "name": "representante_estado_civil",
            "label": "Estado Civil",
            "type": "select",
            "required": False,
            "size": "col-md-4",
            "options": [
                {"value": "solteiro", "label": "Solteiro(a)"},
                {"value": "casado", "label": "Casado(a)"},
                {"value": "divorciado", "label": "Divorciado(a)"},
                {"value": "viuvo", "label": "Viuvo(a)"},
                {"value": "separado", "label": "Separado(a)"},
                {"value": "uniao_estavel", "label": "Uniao Estavel"},
            ],
        },
        {
            "name": "representante_profissao",
            "label": "Profissao",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Ex: Empresario, Socio-administrador",
        },
        {
            "name": "representante_cargo",
            "label": "Cargo/Funcao na Empresa",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Ex: Socio-administrador, Diretor",
        },
        {
            "name": "representante_email",
            "label": "E-mail do Representante",
            "type": "email",
            "required": False,
            "size": "col-md-4",
            "placeholder": "email@exemplo.com",
        },
        {
            "name": "representante_telefone",
            "label": "Telefone do Representante",
            "type": "tel",
            "required": False,
            "size": "col-md-6",
            "placeholder": "(00) 00000-0000",
        },
        {
            "name": "representante_endereco",
            "label": "Endereco do Representante",
            "type": "text",
            "required": False,
            "size": "col-md-6",
            "placeholder": "Endereco completo",
        },
    ]

    section.fields_schema = new_fields
    section.description = (
        "Qualificacao do representante legal para pessoas juridicas (CNPJ)"
    )
    db.session.add(section)
    db.session.commit()

    print(f"[OK] Secao de representante atualizada com {len(new_fields)} campos")
    return True


def main():
    """Função principal."""

    app = create_app()

    with app.app_context():
        # 1. Analisar campos existentes
        cpf_fields = analyze_cpf_fields()

        # 2. Mostrar seção de representante
        representante = show_representante_section()

        if not representante:
            print("\n[INFO] Criando secao de representante...")
            # Criar seção se não existir
            representante = PetitionSection(
                name="Representante Legal",
                slug="representante-legal",
                description="Qualificacao do representante legal para pessoas juridicas (CNPJ)",
                icon="fa-user-tie",
                color="info",
                order=99,
                is_active=True,
                fields_schema=[],
            )
            db.session.add(representante)
            db.session.commit()
            print(f"[OK] Secao criada com ID: {representante.id}")

        # 3. Atualizar campos da seção de representante
        print("\n" + "-" * 80)
        confirm = input("Deseja atualizar os campos da secao de representante? (s/n): ")
        if confirm.lower() == "s":
            update_representante_section_fields()
            representante = PetitionSection.query.filter_by(
                slug="representante-legal"
            ).first()

        # 4. Atualizar campos CPF para CPF/CNPJ
        print("\n" + "-" * 80)
        confirm = input(
            "Deseja converter campos CPF para CPF/CNPJ nas secoes de partes? (s/n): "
        )
        if confirm.lower() == "s":
            update_sections_cpf_to_cpf_cnpj(representante.id)

        # 5. Mostrar resultado final
        print("\n" + "=" * 80)
        print("RESULTADO FINAL")
        print("=" * 80)
        analyze_cpf_fields()
        show_representante_section()


if __name__ == "__main__":
    main()
