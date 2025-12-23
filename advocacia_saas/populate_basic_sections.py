#!/usr/bin/env python3
"""
Script para popular seções básicas de petições para o sistema dinâmico.
Executar após migrações: python populate_basic_sections.py
"""

import json

from app import create_app, db
from app.models import PetitionSection


def create_basic_sections():
    """Cria seções básicas para petições"""

    sections_data = [
        {
            "name": "Qualificação das Partes",
            "slug": "qualificacao-partes",
            "description": "Informações sobre autor e réu da ação",
            "icon": "fa-users",
            "color": "primary",
            "fields_schema": [
                {
                    "name": "autor_nome",
                    "label": "Nome do Autor",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Nome completo do autor da ação",
                },
                {
                    "name": "autor_qualificacao",
                    "label": "Qualificação do Autor",
                    "type": "textarea",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "CPF, RG, endereço completo, profissão, estado civil, etc.",
                },
                {
                    "name": "reu_nome",
                    "label": "Nome do Réu",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Nome completo do réu da ação",
                },
                {
                    "name": "reu_qualificacao",
                    "label": "Qualificação do Réu",
                    "type": "textarea",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "CPF, RG, endereço completo, profissão, estado civil, etc.",
                },
            ],
        },
        {
            "name": "Dos Fatos",
            "slug": "dos-fatos",
            "description": "Narrativa dos fatos que originaram a demanda",
            "icon": "fa-book-open",
            "color": "info",
            "fields_schema": [
                {
                    "name": "fatos",
                    "label": "Narrativa dos Fatos",
                    "type": "textarea",
                    "required": True,
                    "size": "col-md-12",
                    "placeholder": "Descreva detalhadamente os fatos que motivaram a presente ação...",
                }
            ],
        },
        {
            "name": "Do Direito",
            "slug": "do-direito",
            "description": "Fundamentação jurídica da ação",
            "icon": "fa-balance-scale",
            "color": "success",
            "fields_schema": [
                {
                    "name": "fundamentacao_juridica",
                    "label": "Fundamentação Jurídica",
                    "type": "textarea",
                    "required": True,
                    "size": "col-md-12",
                    "placeholder": "Cite os dispositivos legais aplicáveis ao caso...",
                }
            ],
        },
        {
            "name": "Dos Pedidos",
            "slug": "dos-pedidos",
            "description": "Pedidos formulados na petição inicial",
            "icon": "fa-list-check",
            "color": "warning",
            "fields_schema": [
                {
                    "name": "pedidos",
                    "label": "Pedidos",
                    "type": "textarea",
                    "required": True,
                    "size": "col-md-12",
                    "placeholder": "Formule os pedidos da ação...",
                }
            ],
        },
        {
            "name": "Do Valor da Causa",
            "slug": "valor-causa",
            "description": "Valor atribuído à causa",
            "icon": "fa-dollar-sign",
            "color": "danger",
            "fields_schema": [
                {
                    "name": "valor_causa",
                    "label": "Valor da Causa (R$)",
                    "type": "number",
                    "required": False,
                    "size": "col-md-6",
                    "placeholder": "0.00",
                },
                {
                    "name": "justificativa_valor",
                    "label": "Justificativa do Valor",
                    "type": "textarea",
                    "required": False,
                    "size": "col-md-6",
                    "placeholder": "Explique como chegou ao valor da causa...",
                },
            ],
        },
        {
            "name": "Cabeçalho do Processo",
            "slug": "cabecalho-processo",
            "description": "Informações do foro e vara competente",
            "icon": "fa-landmark",
            "color": "secondary",
            "fields_schema": [
                {
                    "name": "foro",
                    "label": "Foro",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Ex: Foro Central da Comarca de São Paulo",
                },
                {
                    "name": "vara",
                    "label": "Vara",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Ex: 1ª Vara Cível",
                },
                {
                    "name": "processo_numero",
                    "label": "Número do Processo",
                    "type": "text",
                    "required": False,
                    "size": "col-md-6",
                    "placeholder": "Caso já exista processo",
                },
                {
                    "name": "comarca",
                    "label": "Comarca",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Ex: São Paulo/SP",
                },
            ],
        },
        {
            "name": "Assinatura",
            "slug": "assinatura",
            "description": "Informações para assinatura da petição",
            "icon": "fa-signature",
            "color": "dark",
            "fields_schema": [
                {
                    "name": "advogado_nome",
                    "label": "Nome do Advogado",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Nome completo do advogado",
                },
                {
                    "name": "advogado_oab",
                    "label": "OAB",
                    "type": "text",
                    "required": True,
                    "size": "col-md-6",
                    "placeholder": "Número da OAB (UF)",
                },
                {
                    "name": "cidade_assinatura",
                    "label": "Cidade",
                    "type": "text",
                    "required": True,
                    "size": "col-md-4",
                    "placeholder": "Cidade da assinatura",
                },
                {
                    "name": "data_assinatura",
                    "label": "Data",
                    "type": "date",
                    "required": True,
                    "size": "col-md-4",
                    "placeholder": "Data da assinatura",
                },
                {
                    "name": "estado_assinatura",
                    "label": "Estado",
                    "type": "text",
                    "required": True,
                    "size": "col-md-4",
                    "placeholder": "Estado (UF)",
                },
            ],
        },
    ]

    app = create_app()
    with app.app_context():
        created_count = 0
        updated_count = 0

        for section_data in sections_data:
            # Verificar se já existe
            existing = PetitionSection.query.filter_by(
                slug=section_data["slug"]
            ).first()

            if existing:
                # Atualizar se necessário
                existing.name = section_data["name"]
                existing.description = section_data["description"]
                existing.icon = section_data["icon"]
                existing.color = section_data["color"]
                existing.fields_schema = section_data["fields_schema"]
                updated_count += 1
                print(f"✓ Atualizado: {existing.name}")
            else:
                # Criar novo
                section = PetitionSection(
                    name=section_data["name"],
                    slug=section_data["slug"],
                    description=section_data["description"],
                    icon=section_data["icon"],
                    color=section_data["color"],
                    fields_schema=section_data["fields_schema"],
                )
                db.session.add(section)
                created_count += 1
                print(f"✓ Criado: {section.name}")

        db.session.commit()
        print(f"\n📊 Resumo: {created_count} criados, {updated_count} atualizados")
        print("🎉 Seções básicas populadas com sucesso!")


if __name__ == "__main__":
    create_basic_sections()
