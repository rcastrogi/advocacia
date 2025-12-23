#!/usr/bin/env python3
"""
Script para criar exemplos de tipos de petição usando o sistema dinâmico.
Cria vários tipos comuns de ações judiciais.
"""

import json
import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar a configuração da aplicação
from app import db
from app.models import PetitionType, PetitionTypeSection, PetitionSection, PetitionTemplate

# Configurar Flask app para scripts
from flask import Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/advocacia_saas')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar SQLAlchemy com a app
db.init_app(app)

def create_petition_examples():
    """Cria exemplos de tipos de petição"""

    with app.app_context():
        # Buscar seções existentes
        sections = {s.slug: s for s in PetitionSection.query.all()}

        # Criar seções adicionais se necessário
        additional_sections = [
            {
                "name": "Do Pedido de Alimentos",
                "slug": "pedido-alimentos",
                "description": "Especificações sobre o pedido de alimentos",
                "icon": "fa-utensils",
                "color": "success",
                "fields_schema": [
                    {
                        "name": "tipo_alimentos",
                        "label": "Tipo de Alimentos",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "provisorios", "label": "Provisórios"},
                            {"value": "definitivos", "label": "Definitivos"},
                            {"value": "provisorios_definitivos", "label": "Provisórios e Definitivos"}
                        ]
                    },
                    {
                        "name": "valor_pretendido",
                        "label": "Valor Pretendido (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "justificativa_valor",
                        "label": "Justificativa do Valor",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Explique como chegou ao valor pretendido..."
                    }
                ]
            },
            {
                "name": "Do Regime de Bens",
                "slug": "regime-bens",
                "description": "Informações sobre o regime de bens do casamento",
                "icon": "fa-ring",
                "color": "danger",
                "fields_schema": [
                    {
                        "name": "regime_casamento",
                        "label": "Regime de Bens",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "comunhao_parcial", "label": "Comunhão Parcial de Bens"},
                            {"value": "comunhao_universal", "label": "Comunhão Universal de Bens"},
                            {"value": "separacao_total", "label": "Separação Total de Bens"},
                            {"value": "participacao_final", "label": "Participação Final nos Aquestos"}
                        ]
                    },
                    {
                        "name": "data_casamento",
                        "label": "Data do Casamento",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "pacto_antenupcial",
                        "label": "Pacto Antenupcial",
                        "type": "select",
                        "required": False,
                        "size": "col-md-6",
                        "options": [
                            {"value": "sim", "label": "Sim"},
                            {"value": "nao", "label": "Não"}
                        ]
                    }
                ]
            },
            {
                "name": "Da Reclamação Trabalhista",
                "slug": "reclamacao-trabalhista",
                "description": "Detalhes da reclamação trabalhista",
                "icon": "fa-briefcase",
                "color": "warning",
                "fields_schema": [
                    {
                        "name": "data_admissao",
                        "label": "Data de Admissão",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "data_demissao",
                        "label": "Data de Demissão",
                        "type": "date",
                        "required": False,
                        "size": "col-md-6"
                    },
                    {
                        "name": "cargo",
                        "label": "Cargo/Função",
                        "type": "text",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "Ex: Analista de Sistemas"
                    },
                    {
                        "name": "salario",
                        "label": "Último Salário (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "horario_trabalho",
                        "label": "Horário de Trabalho",
                        "type": "text",
                        "required": False,
                        "size": "col-md-6",
                        "placeholder": "Ex: 08:00 às 18:00"
                    },
                    {
                        "name": "motivo_reclamacao",
                        "label": "Motivo da Reclamação",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Descreva os direitos violados..."
                    }
                ]
            },
            {
                "name": "Da Cobrança",
                "slug": "da-cobranca",
                "description": "Detalhes da cobrança",
                "icon": "fa-money-bill",
                "color": "info",
                "fields_schema": [
                    {
                        "name": "valor_cobrado",
                        "label": "Valor Cobrado (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "data_vencimento",
                        "label": "Data de Vencimento",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "origem_divida",
                        "label": "Origem da Dívida",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Descreva a origem da dívida..."
                    }
                ]
            }
        ]

        # Criar seções adicionais
        for section_data in additional_sections:
            if section_data['slug'] not in sections:
                section = PetitionSection(
                    name=section_data['name'],
                    slug=section_data['slug'],
                    description=section_data['description'],
                    icon=section_data['icon'],
                    color=section_data['color'],
                    fields_schema=section_data['fields_schema']
                )
                db.session.add(section)
                sections[section.slug] = section
                print(f"✓ Criada seção adicional: {section.name}")

        db.session.commit()

        # Recarregar seções
        sections = {s.slug: s for s in PetitionSection.query.all()}

        # Definir tipos de petição com suas configurações
        petition_types_data = [
            {
                "name": "Ação de Alimentos",
                "slug": "acao-de-alimentos",
                "description": "Ação para pleitear pensão alimentícia",
                "category": "familia",
                "icon": "fa-utensils",
                "color": "success",
                "base_price": 200.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dos-fatos",
                    "pedido-alimentos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação de Divórcio Litigioso",
                "slug": "acao-de-divorcio-litigioso",
                "description": "Ação de divórcio com contestação",
                "category": "familia",
                "icon": "fa-heart-broken",
                "color": "danger",
                "base_price": 300.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "regime-bens",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Reclamação Trabalhista",
                "slug": "reclamacao-trabalhista",
                "description": "Ação trabalhista para pleitear direitos",
                "category": "trabalhista",
                "icon": "fa-briefcase",
                "color": "warning",
                "base_price": 250.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "reclamacao-trabalhista",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação de Cobrança",
                "slug": "acao-de-cobranca",
                "description": "Ação para cobrança de dívida",
                "category": "civel",
                "icon": "fa-money-bill",
                "color": "info",
                "base_price": 180.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "da-cobranca",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            }
        ]

        # Criar tipos de petição
        for pt_data in petition_types_data:
            # Verificar se já existe
            existing = PetitionType.query.filter_by(slug=pt_data['slug']).first()
            if existing:
                print(f"⚠️ Tipo já existe: {existing.name}")
                continue

            petition_type = PetitionType(
                name=pt_data['name'],
                slug=pt_data['slug'],
                description=pt_data['description'],
                category=pt_data['category'],
                icon=pt_data['icon'],
                color=pt_data['color'],
                is_billable=True,
                base_price=pt_data['base_price'],
                use_dynamic_form=True,
                is_implemented=True,
                is_active=True
            )

            db.session.add(petition_type)
            db.session.commit()

            # Configurar seções
            order = 1
            for section_slug in pt_data['sections']:
                if section_slug in sections:
                    config = PetitionTypeSection(
                        petition_type_id=petition_type.id,
                        section_id=sections[section_slug].id,
                        order=order,
                        is_required=True,
                        is_expanded=True
                    )
                    db.session.add(config)
                    order += 1

            db.session.commit()
            print(f"✓ Criado tipo de petição: {petition_type.name} ({len(pt_data['sections'])} seções)")

        print("\n🎉 Exemplos de tipos de petição criados com sucesso!")
        print("\n📋 Tipos criados:")
        for pt_data in petition_types_data:
            print(f"  • {pt_data['name']} → /dynamic/{pt_data['slug']}")

if __name__ == "__main__":
    create_petition_examples()