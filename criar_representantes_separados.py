#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cria seções de representante separadas para Autor e Réu.
"""

import sys
import json
sys.path.insert(0, 'F:/PROJETOS/advocacia/advocacia_saas')

from app import create_app, db
from app.models import PetitionSection
from sqlalchemy import text

app = create_app()

def criar_campos_representante(prefixo, parte):
    """Gera campos do representante com prefixo específico."""
    return [
        # Identificação
        {
            "name": f"{prefixo}_nome",
            "label": f"Nome Completo do Representante ({parte})",
            "type": "text",
            "required": True,
            "size": "col-md-6",
            "placeholder": "Nome completo do representante legal"
        },
        {
            "name": f"{prefixo}_cpf",
            "label": "CPF do Representante",
            "type": "cpf",
            "required": True,
            "size": "col-md-3",
            "placeholder": "000.000.000-00"
        },
        {
            "name": f"{prefixo}_rg",
            "label": "RG do Representante",
            "type": "text",
            "required": False,
            "size": "col-md-3",
            "placeholder": "00.000.000-0"
        },
        # Dados pessoais
        {
            "name": f"{prefixo}_nacionalidade",
            "label": "Nacionalidade",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Brasileiro(a)"
        },
        {
            "name": f"{prefixo}_estado_civil",
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
            "name": f"{prefixo}_profissao",
            "label": "Profissão",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Ex: Empresário, Administrador"
        },
        # Cargo na empresa
        {
            "name": f"{prefixo}_cargo",
            "label": "Cargo/Função na Empresa",
            "type": "text",
            "required": False,
            "size": "col-md-6",
            "placeholder": "Ex: Sócio-administrador, Diretor"
        },
        {
            "name": f"{prefixo}_orgao_emissor",
            "label": "Órgão Emissor RG",
            "type": "text",
            "required": False,
            "size": "col-md-3",
            "placeholder": "SSP/SP"
        },
        {
            "name": f"{prefixo}_data_nascimento",
            "label": "Data de Nascimento",
            "type": "date",
            "required": False,
            "size": "col-md-3"
        },
        # Endereço completo
        {
            "name": f"{prefixo}_cep",
            "label": "CEP",
            "type": "cep",
            "required": False,
            "size": "col-md-3",
            "placeholder": "00000-000"
        },
        {
            "name": f"{prefixo}_logradouro",
            "label": "Logradouro/Rua",
            "type": "text",
            "required": False,
            "size": "col-md-6",
            "placeholder": "Rua, Avenida, etc."
        },
        {
            "name": f"{prefixo}_numero",
            "label": "Número",
            "type": "text",
            "required": False,
            "size": "col-md-3",
            "placeholder": "Nº"
        },
        {
            "name": f"{prefixo}_complemento",
            "label": "Complemento",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Apto, Sala, Bloco"
        },
        {
            "name": f"{prefixo}_bairro",
            "label": "Bairro",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Bairro"
        },
        {
            "name": f"{prefixo}_cidade",
            "label": "Cidade",
            "type": "text",
            "required": False,
            "size": "col-md-4",
            "placeholder": "Cidade"
        },
        {
            "name": f"{prefixo}_estado",
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
            "name": f"{prefixo}_telefone",
            "label": "Telefone Fixo",
            "type": "tel",
            "required": False,
            "size": "col-md-3",
            "placeholder": "(00) 0000-0000"
        },
        {
            "name": f"{prefixo}_celular",
            "label": "Celular",
            "type": "tel",
            "required": False,
            "size": "col-md-3",
            "placeholder": "(00) 00000-0000"
        },
        {
            "name": f"{prefixo}_email",
            "label": "E-mail",
            "type": "email",
            "required": False,
            "size": "col-md-6",
            "placeholder": "email@exemplo.com"
        }
    ]


with app.app_context():
    # 1. Criar/atualizar seção de Representante do AUTOR
    rep_autor = PetitionSection.query.filter_by(slug='representante-autor').first()
    
    if not rep_autor:
        rep_autor = PetitionSection(
            name="Representante Legal do Autor",
            slug="representante-autor",
            description="Qualificação do representante legal do autor (pessoa jurídica)",
            icon="fa-user-tie",
            color="primary",
            order=100,
            is_active=True
        )
        db.session.add(rep_autor)
        db.session.commit()
        print(f"[CRIADO] Secao 'Representante Legal do Autor' (ID: {rep_autor.id})")
    else:
        print(f"[EXISTE] Secao 'Representante Legal do Autor' (ID: {rep_autor.id})")
    
    # Atualizar campos
    campos_autor = criar_campos_representante("rep_autor", "Autor")
    fields_json = json.dumps(campos_autor, ensure_ascii=False)
    db.session.execute(
        text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
        {"fields": fields_json, "id": rep_autor.id}
    )
    
    # 2. Criar/atualizar seção de Representante do RÉU
    rep_reu = PetitionSection.query.filter_by(slug='representante-reu').first()
    
    if not rep_reu:
        rep_reu = PetitionSection(
            name="Representante Legal do Réu",
            slug="representante-reu",
            description="Qualificação do representante legal do réu (pessoa jurídica)",
            icon="fa-user-tie",
            color="danger",
            order=101,
            is_active=True
        )
        db.session.add(rep_reu)
        db.session.commit()
        print(f"[CRIADO] Secao 'Representante Legal do Réu' (ID: {rep_reu.id})")
    else:
        print(f"[EXISTE] Secao 'Representante Legal do Réu' (ID: {rep_reu.id})")
    
    # Atualizar campos
    campos_reu = criar_campos_representante("rep_reu", "Réu")
    fields_json = json.dumps(campos_reu, ensure_ascii=False)
    db.session.execute(
        text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
        {"fields": fields_json, "id": rep_reu.id}
    )
    
    # 3. Criar seção de Representante do TERCEIRO INTERESSADO
    rep_terceiro = PetitionSection.query.filter_by(slug='representante-terceiro').first()
    
    if not rep_terceiro:
        rep_terceiro = PetitionSection(
            name="Representante Legal do Terceiro",
            slug="representante-terceiro",
            description="Qualificação do representante legal do terceiro interessado (pessoa jurídica)",
            icon="fa-user-tie",
            color="info",
            order=102,
            is_active=True
        )
        db.session.add(rep_terceiro)
        db.session.commit()
        print(f"[CRIADO] Secao 'Representante Legal do Terceiro' (ID: {rep_terceiro.id})")
    else:
        print(f"[EXISTE] Secao 'Representante Legal do Terceiro' (ID: {rep_terceiro.id})")
    
    # Atualizar campos
    campos_terceiro = criar_campos_representante("rep_terceiro", "Terceiro")
    fields_json = json.dumps(campos_terceiro, ensure_ascii=False)
    db.session.execute(
        text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
        {"fields": fields_json, "id": rep_terceiro.id}
    )
    
    db.session.commit()
    
    # 4. Atualizar vínculos dos campos cpf_cnpj
    print("\n" + "=" * 60)
    print("ATUALIZANDO VINCULOS DOS CAMPOS CPF/CNPJ")
    print("=" * 60)
    
    # Obter IDs das novas seções
    db.session.expire_all()
    rep_autor = PetitionSection.query.filter_by(slug='representante-autor').first()
    rep_reu = PetitionSection.query.filter_by(slug='representante-reu').first()
    rep_terceiro = PetitionSection.query.filter_by(slug='representante-terceiro').first()
    
    # Mapeamento: seção -> seção de representante correspondente
    vinculos = {
        "autor": rep_autor.id,
        "autor-peticionario": rep_autor.id,
        "reu": rep_reu.id,
        "reu-acusado": rep_reu.id,
        "terceiro-interessado": rep_terceiro.id,
    }
    
    for section_slug, rep_id in vinculos.items():
        section = PetitionSection.query.filter_by(slug=section_slug).first()
        if not section:
            print(f"[AVISO] Secao '{section_slug}' nao encontrada")
            continue
        
        fields = list(section.fields_schema or [])
        modified = False
        
        for field in fields:
            if field.get("type") == "cpf_cnpj":
                field["linked_section_id"] = rep_id
                field["linked_section_trigger"] = "cnpj"
                modified = True
                print(f"[OK] {section_slug}.{field.get('name')} -> Representante ID {rep_id}")
        
        if modified:
            fields_json = json.dumps(fields, ensure_ascii=False)
            db.session.execute(
                text("UPDATE petition_sections SET fields_schema = :fields WHERE id = :id"),
                {"fields": fields_json, "id": section.id}
            )
    
    db.session.commit()
    
    # 5. Resumo final
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    
    print(f"\nSecoes de Representante criadas:")
    print(f"  - Representante do Autor (ID: {rep_autor.id}) - {len(rep_autor.fields_schema)} campos")
    print(f"  - Representante do Reu (ID: {rep_reu.id}) - {len(rep_reu.fields_schema)} campos")
    print(f"  - Representante do Terceiro (ID: {rep_terceiro.id}) - {len(rep_terceiro.fields_schema)} campos")
    
    print(f"\nVinculos:")
    print(f"  - autor.autor_cpf -> Representante do Autor")
    print(f"  - autor-peticionario.documento_numero -> Representante do Autor")
    print(f"  - reu.reu_cpf -> Representante do Reu")
    print(f"  - reu-acusado.documento_numero -> Representante do Reu")
    print(f"  - terceiro-interessado.documento_numero -> Representante do Terceiro")
