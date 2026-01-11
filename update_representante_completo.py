#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza a seção de representante legal com todos os campos necessários.
"""

import sys
import json
sys.path.insert(0, 'F:/PROJETOS/advocacia/advocacia_saas')

from app import create_app, db
from app.models import PetitionSection
from sqlalchemy import text

app = create_app()

# Campos completos do representante legal
campos_representante = [
    # Identificação
    {
        "name": "representante_nome",
        "label": "Nome Completo do Representante",
        "type": "text",
        "required": True,
        "size": "col-md-6",
        "placeholder": "Nome completo do representante legal"
    },
    {
        "name": "representante_cpf",
        "label": "CPF do Representante",
        "type": "cpf",
        "required": True,
        "size": "col-md-3",
        "placeholder": "000.000.000-00"
    },
    {
        "name": "representante_rg",
        "label": "RG do Representante",
        "type": "text",
        "required": False,
        "size": "col-md-3",
        "placeholder": "00.000.000-0"
    },
    # Dados pessoais
    {
        "name": "representante_nacionalidade",
        "label": "Nacionalidade",
        "type": "text",
        "required": False,
        "size": "col-md-4",
        "placeholder": "Brasileiro(a)"
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
            {"value": "viuvo", "label": "Viúvo(a)"},
            {"value": "separado", "label": "Separado(a)"},
            {"value": "uniao_estavel", "label": "União Estável"}
        ]
    },
    {
        "name": "representante_profissao",
        "label": "Profissão",
        "type": "text",
        "required": False,
        "size": "col-md-4",
        "placeholder": "Ex: Empresário, Administrador"
    },
    # Cargo na empresa
    {
        "name": "representante_cargo",
        "label": "Cargo/Função na Empresa",
        "type": "text",
        "required": False,
        "size": "col-md-6",
        "placeholder": "Ex: Sócio-administrador, Diretor, Procurador"
    },
    {
        "name": "representante_data_nascimento",
        "label": "Data de Nascimento",
        "type": "date",
        "required": False,
        "size": "col-md-3"
    },
    {
        "name": "representante_orgao_emissor",
        "label": "Órgão Emissor RG",
        "type": "text",
        "required": False,
        "size": "col-md-3",
        "placeholder": "SSP/SP"
    },
    # Endereço completo
    {
        "name": "representante_cep",
        "label": "CEP",
        "type": "cep",
        "required": False,
        "size": "col-md-3",
        "placeholder": "00000-000"
    },
    {
        "name": "representante_logradouro",
        "label": "Logradouro/Rua",
        "type": "text",
        "required": False,
        "size": "col-md-6",
        "placeholder": "Rua, Avenida, etc."
    },
    {
        "name": "representante_numero",
        "label": "Número",
        "type": "text",
        "required": False,
        "size": "col-md-3",
        "placeholder": "Nº"
    },
    {
        "name": "representante_complemento",
        "label": "Complemento",
        "type": "text",
        "required": False,
        "size": "col-md-4",
        "placeholder": "Apto, Sala, Bloco"
    },
    {
        "name": "representante_bairro",
        "label": "Bairro",
        "type": "text",
        "required": False,
        "size": "col-md-4",
        "placeholder": "Bairro"
    },
    {
        "name": "representante_cidade",
        "label": "Cidade",
        "type": "text",
        "required": False,
        "size": "col-md-4",
        "placeholder": "Cidade"
    },
    {
        "name": "representante_estado",
        "label": "Estado",
        "type": "select",
        "required": False,
        "size": "col-md-3",
        "options": [
            {"value": "AC", "label": "Acre"},
            {"value": "AL", "label": "Alagoas"},
            {"value": "AP", "label": "Amapá"},
            {"value": "AM", "label": "Amazonas"},
            {"value": "BA", "label": "Bahia"},
            {"value": "CE", "label": "Ceará"},
            {"value": "DF", "label": "Distrito Federal"},
            {"value": "ES", "label": "Espírito Santo"},
            {"value": "GO", "label": "Goiás"},
            {"value": "MA", "label": "Maranhão"},
            {"value": "MT", "label": "Mato Grosso"},
            {"value": "MS", "label": "Mato Grosso do Sul"},
            {"value": "MG", "label": "Minas Gerais"},
            {"value": "PA", "label": "Pará"},
            {"value": "PB", "label": "Paraíba"},
            {"value": "PR", "label": "Paraná"},
            {"value": "PE", "label": "Pernambuco"},
            {"value": "PI", "label": "Piauí"},
            {"value": "RJ", "label": "Rio de Janeiro"},
            {"value": "RN", "label": "Rio Grande do Norte"},
            {"value": "RS", "label": "Rio Grande do Sul"},
            {"value": "RO", "label": "Rondônia"},
            {"value": "RR", "label": "Roraima"},
            {"value": "SC", "label": "Santa Catarina"},
            {"value": "SP", "label": "São Paulo"},
            {"value": "SE", "label": "Sergipe"},
            {"value": "TO", "label": "Tocantins"}
        ]
    },
    # Contato
    {
        "name": "representante_telefone",
        "label": "Telefone Fixo",
        "type": "tel",
        "required": False,
        "size": "col-md-3",
        "placeholder": "(00) 0000-0000"
    },
    {
        "name": "representante_celular",
        "label": "Celular",
        "type": "tel",
        "required": False,
        "size": "col-md-3",
        "placeholder": "(00) 00000-0000"
    },
    {
        "name": "representante_email",
        "label": "E-mail",
        "type": "email",
        "required": False,
        "size": "col-md-6",
        "placeholder": "email@exemplo.com"
    }
]

with app.app_context():
    rep = PetitionSection.query.filter_by(slug='representante-legal').first()
    
    if rep:
        print(f"Atualizando secao '{rep.name}' (ID: {rep.id})")
        print(f"Campos anteriores: {len(rep.fields_schema)}")
        
        # Atualizar via SQL direto para garantir persistência
        fields_json = json.dumps(campos_representante, ensure_ascii=False)
        
        db.session.execute(
            text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
            {"fields": fields_json, "id": rep.id}
        )
        db.session.commit()
        
        # Verificar
        db.session.expire_all()
        rep = PetitionSection.query.filter_by(slug='representante-legal').first()
        
        print(f"Campos atuais: {len(rep.fields_schema)}")
        print("\nCampos:")
        for i, f in enumerate(rep.fields_schema, 1):
            print(f"  {i:2}. {f.get('name'):35} | {f.get('type'):10}")
    else:
        print("Secao nao encontrada!")
