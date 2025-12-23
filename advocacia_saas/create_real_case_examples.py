#!/usr/bin/env python3
"""
Script para criar exemplos REALISTAS de tipos de petição usando o sistema dinâmico.
Cria tipos de ações baseados em casos reais comuns no direito brasileiro.
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

def create_real_case_examples():
    """Cria exemplos realistas baseados em casos reais"""

    with app.app_context():
        # Buscar seções existentes
        sections = {s.slug: s for s in PetitionSection.query.all()}

        # Criar seções específicas para casos reais
        real_case_sections = [
            {
                "name": "Dados do Acidente de Trânsito",
                "slug": "dados-acidente-transito",
                "description": "Informações detalhadas sobre o acidente",
                "icon": "fa-car-crash",
                "color": "danger",
                "fields_schema": [
                    {
                        "name": "data_acidente",
                        "label": "Data do Acidente",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "hora_acidente",
                        "label": "Horário do Acidente",
                        "type": "time",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "local_acidente",
                        "label": "Local do Acidente",
                        "type": "text",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Ex: Avenida Paulista, altura do nº 1000, São Paulo/SP"
                    },
                    {
                        "name": "tipo_acidente",
                        "label": "Tipo de Acidente",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "colisao_traseira", "label": "Colisão Traseira"},
                            {"value": "colisao_lateral", "label": "Colisão Lateral"},
                            {"value": "atropelamento", "label": "Atropelamento"},
                            {"value": "capotamento", "label": "Capotamento"},
                            {"value": "saida_pista", "label": "Saída de Pista"},
                            {"value": "outro", "label": "Outro"}
                        ]
                    },
                    {
                        "name": "veiculo_autor",
                        "label": "Veículo do Autor",
                        "type": "text",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "Ex: Fiat Uno, placa ABC-1234"
                    },
                    {
                        "name": "veiculo_reu",
                        "label": "Veículo do Réu",
                        "type": "text",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "Ex: Volkswagen Gol, placa XYZ-5678"
                    },
                    {
                        "name": "seguradora_reu",
                        "label": "Seguradora do Réu",
                        "type": "text",
                        "required": False,
                        "size": "col-md-6",
                        "placeholder": "Ex: Porto Seguro Seguros"
                    },
                    {
                        "name": "numero_sinistro",
                        "label": "Número do Sinistro",
                        "type": "text",
                        "required": False,
                        "size": "col-md-6",
                        "placeholder": "Ex: 123456789"
                    }
                ]
            },
            {
                "name": "Danos Materiais e Morais",
                "slug": "danos-materiais-morais",
                "description": "Especificação dos danos materiais e morais sofridos",
                "icon": "fa-money-bill-wave",
                "color": "warning",
                "fields_schema": [
                    {
                        "name": "danos_materiais",
                        "label": "Danos Materiais",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Descreva os danos materiais sofridos (consertos do veículo, despesas médicas, etc.)"
                    },
                    {
                        "name": "valor_danos_materiais",
                        "label": "Valor dos Danos Materiais (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "danos_morais",
                        "label": "Danos Morais",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Descreva os danos morais sofridos (sofrimento, angústia, etc.)"
                    },
                    {
                        "name": "valor_danos_morais",
                        "label": "Valor dos Danos Morais (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "valor_total_pretendido",
                        "label": "Valor Total Pretendido (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    }
                ]
            },
            {
                "name": "Dados do Contrato de Trabalho",
                "slug": "dados-contrato-trabalho",
                "description": "Informações sobre o contrato de trabalho e rescisão",
                "icon": "fa-file-contract",
                "color": "primary",
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
                        "label": "Data da Demissão/Rescisão",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "cargo_funcao",
                        "label": "Cargo/Função",
                        "type": "text",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "Ex: Analista de Recursos Humanos"
                    },
                    {
                        "name": "salario_base",
                        "label": "Salário Base (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "tipo_contrato",
                        "label": "Tipo de Contrato",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "experiencia", "label": "Contrato de Experiência"},
                            {"value": "determinado", "label": "Prazo Determinado"},
                            {"value": "indeterminado", "label": "Prazo Indeterminado"},
                            {"value": "temporario", "label": "Temporário"}
                        ]
                    },
                    {
                        "name": "tipo_rescisao",
                        "label": "Tipo de Rescisão",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "sem_justa_causa", "label": "Sem Justa Causa"},
                            {"value": "com_justa_causa", "label": "Com Justa Causa"},
                            {"value": "pedido_demissao", "label": "Pedido de Demissão"},
                            {"value": "rescisao_indireta", "label": "Rescisão Indireta"},
                            {"value": "culpa_reciproca", "label": "Culpa Recíproca"}
                        ]
                    },
                    {
                        "name": "motivo_demissao",
                        "label": "Motivo da Demissão",
                        "type": "textarea",
                        "required": False,
                        "size": "col-md-12",
                        "placeholder": "Descreva o motivo alegado pela empresa para a demissão"
                    },
                    {
                        "name": "verbas_rescisorias",
                        "label": "Verbas Rescisorias Pleiteadas",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Liste as verbas rescisórias não pagas (saldo de salário, férias, 13º, FGTS, etc.)"
                    }
                ]
            },
            {
                "name": "Dados do Imóvel",
                "slug": "dados-imovel",
                "description": "Informações sobre o imóvel objeto da ação",
                "icon": "fa-home",
                "color": "info",
                "fields_schema": [
                    {
                        "name": "tipo_imovel",
                        "label": "Tipo de Imóvel",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "apartamento", "label": "Apartamento"},
                            {"value": "casa", "label": "Casa"},
                            {"value": "terreno", "label": "Terreno"},
                            {"value": "sala_comercial", "label": "Sala Comercial"},
                            {"value": "galpao", "label": "Galpão"},
                            {"value": "outro", "label": "Outro"}
                        ]
                    },
                    {
                        "name": "endereco_imovel",
                        "label": "Endereço Completo",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Rua, número, complemento, bairro, cidade/UF, CEP"
                    },
                    {
                        "name": "matricula_imovel",
                        "label": "Matrícula do Imóvel",
                        "type": "text",
                        "required": False,
                        "size": "col-md-6",
                        "placeholder": "Ex: 123456 do 1º CRI de São Paulo"
                    },
                    {
                        "name": "valor_aluguel",
                        "label": "Valor do Aluguel (R$)",
                        "type": "number",
                        "required": False,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "data_inicio_contrato",
                        "label": "Data de Início do Contrato",
                        "type": "date",
                        "required": False,
                        "size": "col-md-6"
                    },
                    {
                        "name": "data_fim_contrato",
                        "label": "Data de Fim do Contrato",
                        "type": "date",
                        "required": False,
                        "size": "col-md-6"
                    }
                ]
            },
            {
                "name": "Dados do Consumo",
                "slug": "dados-consumo",
                "description": "Informações sobre o produto/serviço consumido",
                "icon": "fa-shopping-cart",
                "color": "success",
                "fields_schema": [
                    {
                        "name": "tipo_produto_servico",
                        "label": "Tipo de Produto/Serviço",
                        "type": "select",
                        "required": True,
                        "size": "col-md-6",
                        "options": [
                            {"value": "produto", "label": "Produto"},
                            {"value": "servico", "label": "Serviço"},
                            {"value": "contrato_bancario", "label": "Contrato Bancário"},
                            {"value": "seguro", "label": "Seguro"},
                            {"value": "plano_saude", "label": "Plano de Saúde"},
                            {"value": "outro", "label": "Outro"}
                        ]
                    },
                    {
                        "name": "nome_produto_servico",
                        "label": "Nome do Produto/Serviço",
                        "type": "text",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "Ex: Celular Samsung Galaxy, Plano de Saúde Unimed"
                    },
                    {
                        "name": "data_compra_contratacao",
                        "label": "Data da Compra/Contratação",
                        "type": "date",
                        "required": True,
                        "size": "col-md-6"
                    },
                    {
                        "name": "valor_pago",
                        "label": "Valor Pago (R$)",
                        "type": "number",
                        "required": True,
                        "size": "col-md-6",
                        "placeholder": "0.00"
                    },
                    {
                        "name": "defeito_problema",
                        "label": "Defeito/Problema Apresentado",
                        "type": "textarea",
                        "required": True,
                        "size": "col-md-12",
                        "placeholder": "Descreva detalhadamente o defeito ou problema apresentado"
                    },
                    {
                        "name": "tentativas_solucao",
                        "label": "Tentativas de Solução",
                        "type": "textarea",
                        "required": False,
                        "size": "col-md-12",
                        "placeholder": "Descreva as tentativas de contato com a empresa e soluções oferecidas"
                    }
                ]
            }
        ]

        # Criar seções para casos reais
        for section_data in real_case_sections:
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
                print(f"✓ Criada seção realista: {section.name}")

        db.session.commit()

        # Recarregar seções
        sections = {s.slug: s for s in PetitionSection.query.all()}

        # Definir tipos de petição REALISTAS baseados em casos reais
        real_petition_types = [
            {
                "name": "Ação de Indenização por Acidente de Trânsito",
                "slug": "acao-indenizacao-acidente-transito",
                "description": "Ação para reparação de danos causados em acidente de trânsito",
                "category": "civil",
                "icon": "fa-car-crash",
                "color": "danger",
                "base_price": 350.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dados-acidente-transito",
                    "dos-fatos",
                    "danos-materiais-morais",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação Trabalhista - Rescisão Indireta",
                "slug": "acao-trabalhista-rescisao-indireta",
                "description": "Ação trabalhista por rescisão indireta do contrato de trabalho",
                "category": "trabalhista",
                "icon": "fa-gavel",
                "color": "warning",
                "base_price": 280.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dados-contrato-trabalho",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação de Despejo por Fim do Contrato",
                "slug": "acao-despejo-fim-contrato",
                "description": "Ação de despejo por término do contrato de locação",
                "category": "civil",
                "icon": "fa-home",
                "color": "info",
                "base_price": 250.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dados-imovel",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação Revisional de Aluguel",
                "slug": "acao-revisional-aluguel",
                "description": "Ação para revisão do valor do aluguel por reajuste abusivo",
                "category": "civil",
                "icon": "fa-calculator",
                "color": "primary",
                "base_price": 220.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dados-imovel",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação de Responsabilidade Civil do Fornecedor",
                "slug": "acao-consumidor-fornecedor",
                "description": "Ação contra fornecedor por vício do produto/serviço (CDC)",
                "category": "consumidor",
                "icon": "fa-shopping-cart",
                "color": "success",
                "base_price": 180.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dados-consumo",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            },
            {
                "name": "Ação de Cobrança de Honorários Advocatícios",
                "slug": "acao-cobranca-honorarios",
                "description": "Ação para cobrança de honorários advocatícios não pagos",
                "category": "civil",
                "icon": "fa-file-invoice-dollar",
                "color": "secondary",
                "base_price": 200.00,
                "sections": [
                    "cabecalho-processo",
                    "qualificacao-partes",
                    "dos-fatos",
                    "do-direito",
                    "dos-pedidos",
                    "valor-causa",
                    "assinatura"
                ]
            }
        ]

        # Criar tipos de petição realistas
        for pt_data in real_petition_types:
            # Verificar se já existe
            existing = PetitionType.query.filter_by(slug=pt_data['slug']).first()
            if existing:
                print(f"⚠ Tipo já existe: {pt_data['name']}")
                continue

            # Criar novo tipo
            pt = PetitionType(
                name=pt_data['name'],
                slug=pt_data['slug'],
                description=pt_data['description'],
                category=pt_data['category'],
                icon=pt_data['icon'],
                color=pt_data['color'],
                base_price=pt_data['base_price'],
                is_implemented=True,
                is_active=True
            )
            db.session.add(pt)
            db.session.commit()  # Commit aqui para ter o ID
            print(f"✓ Criado tipo realista: {pt.name}")

            # Configurar seções
            for i, section_slug in enumerate(pt_data['sections']):
                if section_slug in sections:
                    config = PetitionTypeSection(
                        petition_type_id=pt.id,
                        section_id=sections[section_slug].id,
                        order=i + 1,
                        is_required=True,
                        is_expanded=(i < 3)  # Expandir primeiras 3 seções
                    )
                    db.session.add(config)

        db.session.commit()
        print(f"\n🎯 Criados {len(real_petition_types)} tipos de petição realistas!")

if __name__ == "__main__":
    create_real_case_examples()