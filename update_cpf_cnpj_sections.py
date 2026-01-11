#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar campos CPF para CPF/CNPJ e criar seção de representante vinculada.

Este script:
1. Cria a seção "Representante Legal" (para pessoas jurídicas)
2. Atualiza todos os campos do tipo 'cpf' para 'cpf_cnpj'
3. Adiciona a propriedade 'linked_section' aos campos cpf_cnpj
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


def create_representante_section():
    """Cria a seção de Representante Legal se não existir."""

    # Verificar se já existe
    existing = PetitionSection.query.filter_by(slug="representante-legal").first()
    if existing:
        print(f"[INFO] Secao 'Representante Legal' ja existe (ID: {existing.id})")
        return existing

    # Campos do representante (pessoa física)
    representante_fields = [
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
            "name": "representante_rg",
            "label": "RG do Representante",
            "type": "text",
            "required": False,
            "size": "col-md-6",
            "placeholder": "00.000.000-0",
        },
        {
            "name": "representante_cargo",
            "label": "Cargo/Funcao na Empresa",
            "type": "text",
            "required": False,
            "size": "col-md-6",
            "placeholder": "Ex: Socio-administrador, Diretor",
        },
        {
            "name": "representante_email",
            "label": "E-mail do Representante",
            "type": "email",
            "required": False,
            "size": "col-md-6",
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
    ]

    # Criar a seção
    section = PetitionSection(
        name="Representante Legal",
        slug="representante-legal",
        description="Qualificacao do representante legal para pessoas juridicas (CNPJ)",
        icon="fa-user-tie",
        color="info",
        order=99,  # Ordem alta para aparecer após outras seções
        is_active=True,
        fields_schema=representante_fields,
    )

    db.session.add(section)
    db.session.commit()

    print(f"[OK] Secao 'Representante Legal' criada com sucesso (ID: {section.id})")
    return section


def update_cpf_fields_to_cpf_cnpj(representante_section_id):
    """
    Atualiza todos os campos do tipo 'cpf' para 'cpf_cnpj' e adiciona
    a propriedade de seção vinculada.
    """

    # Buscar todas as seções com campos
    sections = PetitionSection.query.filter(
        PetitionSection.fields_schema.isnot(None)
    ).all()

    updated_count = 0

    for section in sections:
        # Pular a seção de representante
        if section.slug == "representante-legal":
            continue

        fields = section.fields_schema or []
        if not fields:
            continue

        modified = False
        new_fields = []

        for field in fields:
            field_type = field.get("type", "text")
            field_name = field.get("name", "")

            # Verificar se é um campo CPF que deve ser convertido para CPF/CNPJ
            # Apenas converter campos que representam identificação da parte (autor, réu, etc)
            should_convert = field_type == "cpf" and any(
                keyword in field_name.lower()
                for keyword in [
                    "autor",
                    "reu",
                    "requerente",
                    "requerido",
                    "parte",
                    "cliente",
                ]
            )

            if should_convert:
                # Converter para cpf_cnpj
                field["type"] = "cpf_cnpj"
                field["linked_section_id"] = representante_section_id
                field["linked_section_trigger"] = (
                    "cnpj"  # Mostrar seção quando for CNPJ
                )
                modified = True
                print(
                    f"  -> Campo '{field_name}' convertido para cpf_cnpj na secao '{section.name}'"
                )
                updated_count += 1

            new_fields.append(field)

        if modified:
            section.fields_schema = new_fields
            db.session.add(section)

    db.session.commit()
    return updated_count


def list_current_sections():
    """Lista todas as seções e seus campos para diagnóstico."""

    print("\n" + "=" * 70)
    print("SECOES EXISTENTES NO BANCO")
    print("=" * 70)

    sections = PetitionSection.query.order_by(PetitionSection.order).all()

    for section in sections:
        fields = section.fields_schema or []
        cpf_fields = [f for f in fields if f.get("type") in ["cpf", "cpf_cnpj", "cnpj"]]

        print(f"\n[{section.id}] {section.name} ({section.slug})")
        print(f"    Ativa: {section.is_active} | Campos: {len(fields)}")

        if cpf_fields:
            print("    Campos de CPF/CNPJ:")
            for f in cpf_fields:
                linked = f.get("linked_section_id", "-")
                print(
                    f"      - {f.get('name')}: tipo={f.get('type')}, linked_section={linked}"
                )

        if not fields:
            print("    (sem campos definidos)")


def validate_implementation():
    """Valida se a implementação está correta."""

    print("\n" + "=" * 70)
    print("VALIDACAO DA IMPLEMENTACAO")
    print("=" * 70)

    errors = []
    warnings = []

    # 1. Verificar se a seção de representante existe
    representante = PetitionSection.query.filter_by(slug="representante-legal").first()
    if not representante:
        errors.append("Secao 'representante-legal' nao encontrada")
    else:
        print("[OK] Secao 'representante-legal' existe")

        # Verificar campos da seção
        fields = representante.fields_schema or []
        if len(fields) < 5:
            warnings.append(f"Secao de representante tem apenas {len(fields)} campos")
        else:
            print(f"[OK] Secao de representante tem {len(fields)} campos")

        # Verificar campos obrigatórios
        required_fields = ["representante_nome", "representante_cpf"]
        for rf in required_fields:
            if not any(f.get("name") == rf for f in fields):
                errors.append(
                    f"Campo obrigatorio '{rf}' nao encontrado na secao de representante"
                )
            else:
                print(f"[OK] Campo '{rf}' presente")

    # 2. Verificar campos cpf_cnpj com linked_section
    sections = PetitionSection.query.all()
    cpf_cnpj_fields = []

    for section in sections:
        if section.slug == "representante-legal":
            continue

        fields = section.fields_schema or []
        for field in fields:
            if field.get("type") == "cpf_cnpj":
                cpf_cnpj_fields.append(
                    {
                        "section": section.name,
                        "field": field.get("name"),
                        "linked_section_id": field.get("linked_section_id"),
                    }
                )

    if cpf_cnpj_fields:
        print(f"\n[OK] Encontrados {len(cpf_cnpj_fields)} campos cpf_cnpj:")
        for cf in cpf_cnpj_fields:
            linked = cf.get("linked_section_id")
            status = "COM vinculo" if linked else "SEM vinculo"
            print(f"    - {cf['section']}: {cf['field']} ({status})")

            if not linked:
                warnings.append(
                    f"Campo {cf['field']} em {cf['section']} sem linked_section_id"
                )
    else:
        warnings.append("Nenhum campo cpf_cnpj encontrado nas secoes")

    # Resumo
    print("\n" + "-" * 40)
    if errors:
        print(f"[ERRO] {len(errors)} erro(s) encontrado(s):")
        for e in errors:
            print(f"  X {e}")
    else:
        print("[OK] Nenhum erro encontrado")

    if warnings:
        print(f"[AVISO] {len(warnings)} aviso(s):")
        for w in warnings:
            print(f"  ! {w}")

    return len(errors) == 0


def main():
    """Função principal."""

    print("=" * 70)
    print("ATUALIZACAO DE CAMPOS CPF/CNPJ E SECAO DE REPRESENTANTE")
    print("=" * 70)
    print()

    app = create_app()

    with app.app_context():
        # Mostrar estado atual
        list_current_sections()

        print("\n" + "=" * 70)
        print("INICIANDO ATUALIZACOES")
        print("=" * 70)

        # 1. Criar seção de representante
        print("\n[1/3] Criando secao de Representante Legal...")
        representante_section = create_representante_section()

        # 2. Atualizar campos CPF para CPF/CNPJ
        print("\n[2/3] Atualizando campos CPF para CPF/CNPJ...")
        updated_count = update_cpf_fields_to_cpf_cnpj(representante_section.id)
        print(f"    Total de campos atualizados: {updated_count}")

        # 3. Validar implementação
        print("\n[3/3] Validando implementacao...")
        is_valid = validate_implementation()

        # Mostrar estado final
        list_current_sections()

        if is_valid:
            print("\n" + "=" * 70)
            print("[SUCESSO] Atualizacao concluida com sucesso!")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("[ATENCAO] Atualizacao concluida com alertas")
            print("=" * 70)


if __name__ == "__main__":
    main()
