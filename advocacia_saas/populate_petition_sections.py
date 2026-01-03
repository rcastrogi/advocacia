#!/usr/bin/env python3
"""
Script para criar seções de petições reais e vinculá-las aos tipos de petição.
Popula o banco com modelos de petições completos para testes.
"""

import sys

from app import create_app, db
from app.models import PetitionSection, PetitionType

# Definição das seções padrão reutilizáveis
SECTIONS = [
    {
        "name": "Qualificação das Partes",
        "slug": "qualificacao-partes",
        "description": "Dados dos autores, réus e outras partes envolvidas",
        "icon": "fa-users",
        "color": "info",
        "fields_schema": [
            {
                "name": "author_name",
                "label": "Nome do Autor",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo do autor",
            },
            {
                "name": "author_doc_type",
                "label": "Tipo de Documento",
                "type": "select",
                "required": True,
                "size": "col-md-3",
                "options": [
                    {"value": "cpf", "label": "CPF"},
                    {"value": "cnpj", "label": "CNPJ"},
                ],
            },
            {
                "name": "author_doc_number",
                "label": "Número do Documento",
                "type": "text",
                "required": True,
                "size": "col-md-3",
                "placeholder": "000.000.000-00",
            },
            {
                "name": "defendant_name",
                "label": "Nome do Réu/Denunciado",
                "type": "text",
                "required": True,
                "size": "col-md-6",
                "placeholder": "Nome completo",
            },
            {
                "name": "defendant_doc_type",
                "label": "Tipo de Documento",
                "type": "select",
                "required": False,
                "size": "col-md-3",
                "options": [
                    {"value": "cpf", "label": "CPF"},
                    {"value": "cnpj", "label": "CNPJ"},
                ],
            },
            {
                "name": "defendant_doc_number",
                "label": "Número do Documento",
                "type": "text",
                "required": False,
                "size": "col-md-3",
            },
        ],
    },
    {
        "name": "Endereço e Localização",
        "slug": "endereco-localizacao",
        "description": "Endereços das partes envolvidas",
        "icon": "fa-map-marker-alt",
        "color": "success",
        "fields_schema": [
            {
                "name": "author_cep",
                "label": "CEP do Autor",
                "type": "cep",
                "required": False,
                "size": "col-md-2",
                "placeholder": "00000-000",
            },
            {
                "name": "author_street",
                "label": "Rua/Avenida",
                "type": "text",
                "required": False,
                "size": "col-md-5",
            },
            {
                "name": "author_number",
                "label": "Número",
                "type": "text",
                "required": False,
                "size": "col-md-2",
            },
            {
                "name": "author_neighborhood",
                "label": "Bairro",
                "type": "text",
                "required": False,
                "size": "col-md-3",
            },
            {
                "name": "author_city",
                "label": "Cidade",
                "type": "text",
                "required": False,
                "size": "col-md-4",
            },
            {
                "name": "author_state",
                "label": "Estado",
                "type": "select",
                "required": False,
                "size": "col-md-2",
                "options": [
                    {"value": "SP", "label": "SP"},
                    {"value": "RJ", "label": "RJ"},
                    {"value": "MG", "label": "MG"},
                    {"value": "BA", "label": "BA"},
                    {"value": "RS", "label": "RS"},
                    {"value": "PE", "label": "PE"},
                    {"value": "PR", "label": "PR"},
                    {"value": "DF", "label": "DF"},
                ],
            },
        ],
    },
    {
        "name": "Fatos e Fundamentos",
        "slug": "fatos-fundamentos",
        "description": "Descrição dos fatos relevantes ao caso",
        "icon": "fa-file-text",
        "color": "warning",
        "fields_schema": [
            {
                "name": "case_summary",
                "label": "Resumo do Caso",
                "type": "textarea",
                "required": True,
                "size": "col-md-12",
                "placeholder": "Descrição breve do caso",
                "rows": 3,
            },
            {
                "name": "facts",
                "label": "Fatos da Ação",
                "type": "textarea",
                "required": True,
                "size": "col-md-12",
                "placeholder": "Descreva os fatos relevantes",
                "rows": 5,
            },
            {
                "name": "legal_basis",
                "label": "Fundamentação Legal",
                "type": "textarea",
                "required": True,
                "size": "col-md-12",
                "placeholder": "Cite os artigos e leis aplicáveis",
                "rows": 4,
            },
        ],
    },
    {
        "name": "Pedidos",
        "slug": "pedidos",
        "description": "O que está sendo solicitado ao juiz",
        "icon": "fa-hand-paper",
        "color": "danger",
        "fields_schema": [
            {
                "name": "main_request",
                "label": "Pedido Principal",
                "type": "textarea",
                "required": True,
                "size": "col-md-12",
                "placeholder": "Qual é o pedido principal da ação?",
                "rows": 3,
            },
            {
                "name": "secondary_requests",
                "label": "Pedidos Subsidiários",
                "type": "textarea",
                "required": False,
                "size": "col-md-12",
                "placeholder": "Descreva pedidos alternativos se houver",
                "rows": 3,
            },
            {
                "name": "value",
                "label": "Valor da Causa",
                "type": "number",
                "required": False,
                "size": "col-md-4",
                "step": "0.01",
                "min": "0",
                "prefix": "R$ ",
            },
        ],
    },
    {
        "name": "Provas",
        "slug": "provas",
        "description": "Documentos e provas que sustentam a ação",
        "icon": "fa-file-pdf",
        "color": "secondary",
        "fields_schema": [
            {
                "name": "documents",
                "label": "Documentos Anexados",
                "type": "textarea",
                "required": False,
                "size": "col-md-12",
                "placeholder": "Liste os documentos que acompanham a petição",
                "rows": 3,
            },
            {
                "name": "witnesses",
                "label": "Testemunhas",
                "type": "textarea",
                "required": False,
                "size": "col-md-12",
                "placeholder": "Descreva as testemunhas que podem comprovar os fatos",
                "rows": 3,
            },
            {
                "name": "expert_evidence",
                "label": "Perícia Técnica",
                "type": "textarea",
                "required": False,
                "size": "col-md-12",
                "placeholder": "Indique se há necessidade de perícia",
                "rows": 3,
            },
        ],
    },
    {
        "name": "Conclusão",
        "slug": "conclusao",
        "description": "Observações finais e encerramento",
        "icon": "fa-check-circle",
        "color": "success",
        "fields_schema": [
            {
                "name": "closing_remarks",
                "label": "Observações Finais",
                "type": "textarea",
                "required": False,
                "size": "col-md-12",
                "placeholder": "Adicione qualquer observação final",
                "rows": 3,
            },
            {
                "name": "jurisdiction",
                "label": "Foro Competente",
                "type": "text",
                "required": False,
                "size": "col-md-6",
                "placeholder": "Ex: Comarca de São Paulo",
            },
        ],
    },
]

# Mapeamento: tipo de petição => seções que deve ter
PETITION_TYPE_SECTIONS = {
    "acao-de-cobranca": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "acao-de-alimentos": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "acao-de-divorcio": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "acao-de-reintegracao": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "peticao-inicial-civel": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "guarda-e-regulacao-de-visitas": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "divorcio-consensual": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "pedido-de-habeas-corpus": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "defesa-criminal": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "reclamacao-trabalhista": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "defesa-trabalhista": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "mandado-de-seguranca": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
    "execucao-fiscal": [
        "qualificacao-partes",
        "endereco-localizacao",
        "fatos-fundamentos",
        "pedidos",
        "provas",
        "conclusao",
    ],
}


def populate_sections():
    """Popula o banco com seções e vincula aos tipos de petição"""
    app = create_app()
    with app.app_context():
        try:
            print("📋 Iniciando população de seções de petições...")

            # 1. Criar ou atualizar seções
            print("\n1️⃣ Criando seções...")
            section_map = {}
            for section_data in SECTIONS:
                existing = PetitionSection.query.filter_by(
                    slug=section_data["slug"]
                ).first()
                if existing:
                    print(f"  ✓ Seção '{section_data['name']}' já existe")
                    section_map[section_data["slug"]] = existing
                else:
                    section = PetitionSection(**section_data)
                    db.session.add(section)
                    db.session.commit()
                    section_map[section_data["slug"]] = section
                    print(f"  ✅ Seção '{section_data['name']}' criada")

            # 2. Vincular seções aos tipos de petição
            print("\n2️⃣ Vinculando seções aos tipos de petição...")
            total_links = 0
            for petition_slug, section_slugs in PETITION_TYPE_SECTIONS.items():
                petition_type = PetitionType.query.filter_by(slug=petition_slug).first()
                if not petition_type:
                    print(f"  ⚠️ Tipo de petição '{petition_slug}' não encontrado")
                    continue

                # PetitionTypeSection removed - now only using PetitionModelSection
                # This script is deprecated and no longer needed
                pass

            print(f"\n✨ Population completa!")
            print(f"   📊 Total de seções criadas: {len(SECTIONS)}")
            print(
                f"   🔗 Total de vinculações: Deprecated - using PetitionModelSection only"
            )

            # Verificar resultado - deprecated
            # print("\n📈 Resultado final:")
            # for petition_slug in PETITION_TYPE_SECTIONS.keys():

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = populate_sections()
    sys.exit(0 if success else 1)
