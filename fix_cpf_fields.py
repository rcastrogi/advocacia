#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar diretamente os campos CPF para CPF/CNPJ.
"""

import os
import sys

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import PetitionSection


def update_field(section_slug, field_name, new_type, linked_section_id=None):
    """Atualiza um campo específico em uma seção."""
    
    section = PetitionSection.query.filter_by(slug=section_slug).first()
    if not section:
        print(f"[ERRO] Secao '{section_slug}' nao encontrada")
        return False
    
    fields = section.fields_schema or []
    
    for field in fields:
        if field.get("name") == field_name:
            old_type = field.get("type")
            field["type"] = new_type
            if linked_section_id:
                field["linked_section_id"] = linked_section_id
                field["linked_section_trigger"] = "cnpj"
            
            section.fields_schema = fields
            db.session.add(section)
            db.session.commit()
            
            print(f"[OK] {section.name}: {field_name} ({old_type} -> {new_type})")
            return True
    
    print(f"[AVISO] Campo '{field_name}' nao encontrado em '{section_slug}'")
    return False


def verify_updates():
    """Verifica as atualizações feitas."""
    
    print("\n" + "=" * 80)
    print("VERIFICACAO DE CAMPOS CPF/CNPJ")
    print("=" * 80)
    
    sections = PetitionSection.query.all()
    cpf_cnpj_fields = []
    
    for section in sections:
        fields = section.fields_schema or []
        for field in fields:
            if field.get("type") == "cpf_cnpj":
                cpf_cnpj_fields.append({
                    "section": section.name,
                    "section_slug": section.slug,
                    "field_name": field.get("name"),
                    "label": field.get("label"),
                    "linked_section_id": field.get("linked_section_id"),
                    "linked_section_trigger": field.get("linked_section_trigger")
                })
    
    if cpf_cnpj_fields:
        print(f"\nTotal de campos cpf_cnpj: {len(cpf_cnpj_fields)}\n")
        for cf in cpf_cnpj_fields:
            linked = f"-> secao {cf['linked_section_id']}" if cf['linked_section_id'] else "(sem vinculo)"
            print(f"  - [{cf['section_slug']}] {cf['field_name']} {linked}")
    else:
        print("\n[AVISO] Nenhum campo cpf_cnpj encontrado!")
    
    return cpf_cnpj_fields


def main():
    """Função principal."""
    
    app = create_app()
    
    with app.app_context():
        # ID da seção de representante
        rep = PetitionSection.query.filter_by(slug="representante-legal").first()
        
        if not rep:
            print("[ERRO] Secao de representante nao encontrada!")
            return
        
        rep_id = rep.id
        print(f"ID da secao de representante: {rep_id}")
        
        print("\n" + "=" * 80)
        print("ATUALIZANDO CAMPOS CPF PARA CPF/CNPJ")
        print("=" * 80 + "\n")
        
        # Atualizar campos específicos
        updates = [
            ("autor", "autor_cpf", "cpf_cnpj"),
            ("reu", "reu_cpf", "cpf_cnpj"),
            ("autor-peticionario", "documento_numero", "cpf_cnpj"),
            ("reu-acusado", "documento_numero", "cpf_cnpj"),
            ("terceiro-interessado", "documento_numero", "cpf_cnpj"),
        ]
        
        for section_slug, field_name, new_type in updates:
            update_field(section_slug, field_name, new_type, rep_id)
        
        # Verificar resultado
        verify_updates()
        
        print("\n[CONCLUIDO] Campos atualizados com sucesso!")


if __name__ == "__main__":
    main()
