#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar a implementação completa de CPF/CNPJ com seção de representante.
"""

import os
import sys
import json

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import PetitionSection


def validate_implementation():
    """Valida toda a implementação."""
    
    print("=" * 80)
    print("VALIDACAO DA IMPLEMENTACAO CPF/CNPJ COM SECAO DE REPRESENTANTE")
    print("=" * 80)
    
    errors = []
    warnings = []
    success = []
    
    # 1. Verificar seção de representante
    print("\n[1] Verificando secao de representante legal...")
    rep_section = PetitionSection.query.filter_by(slug="representante-legal").first()
    
    if not rep_section:
        errors.append("Secao 'representante-legal' NAO encontrada!")
    else:
        success.append(f"Secao de representante encontrada (ID: {rep_section.id})")
        
        fields = rep_section.fields_schema or []
        required_fields = ["representante_nome", "representante_cpf"]
        
        for rf in required_fields:
            if any(f.get("name") == rf for f in fields):
                success.append(f"  Campo '{rf}' presente")
            else:
                errors.append(f"  Campo '{rf}' NAO encontrado")
    
    # 2. Verificar campos cpf_cnpj com linked_section_id
    print("\n[2] Verificando campos cpf_cnpj com vinculo...")
    
    sections = PetitionSection.query.all()
    cpf_cnpj_fields = []
    
    for section in sections:
        fields = section.fields_schema or []
        for field in fields:
            if field.get("type") == "cpf_cnpj":
                cpf_cnpj_fields.append({
                    "section_name": section.name,
                    "section_slug": section.slug,
                    "field_name": field.get("name"),
                    "linked_section_id": field.get("linked_section_id"),
                    "linked_section_trigger": field.get("linked_section_trigger")
                })
    
    if cpf_cnpj_fields:
        success.append(f"Encontrados {len(cpf_cnpj_fields)} campos cpf_cnpj:")
        
        for cf in cpf_cnpj_fields:
            linked = cf.get("linked_section_id")
            trigger = cf.get("linked_section_trigger")
            
            if linked and trigger:
                success.append(f"  - [{cf['section_slug']}] {cf['field_name']} -> secao {linked} (trigger: {trigger})")
            elif linked:
                warnings.append(f"  - [{cf['section_slug']}] {cf['field_name']} -> secao {linked} (SEM trigger)")
            else:
                warnings.append(f"  - [{cf['section_slug']}] {cf['field_name']} (SEM vinculo)")
    else:
        errors.append("Nenhum campo cpf_cnpj encontrado!")
    
    # 3. Verificar se os campos vinculados apontam para a seção correta
    print("\n[3] Verificando consistencia dos vinculos...")
    
    if rep_section:
        for cf in cpf_cnpj_fields:
            linked_id = cf.get("linked_section_id")
            if linked_id:
                if linked_id == rep_section.id:
                    success.append(f"  - {cf['field_name']}: vinculo correto")
                else:
                    warnings.append(f"  - {cf['field_name']}: vinculado a secao {linked_id} (esperado: {rep_section.id})")
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DA VALIDACAO")
    print("=" * 80)
    
    if success:
        print(f"\n[OK] {len(success)} verificacao(oes) bem-sucedida(s):")
        for s in success:
            print(f"  + {s}")
    
    if warnings:
        print(f"\n[AVISO] {len(warnings)} aviso(s):")
        for w in warnings:
            print(f"  ! {w}")
    
    if errors:
        print(f"\n[ERRO] {len(errors)} erro(s):")
        for e in errors:
            print(f"  X {e}")
    
    # Status final
    print("\n" + "-" * 80)
    if not errors:
        print("[SUCESSO] Implementacao validada com sucesso!")
        return True
    else:
        print("[FALHA] Implementacao com erros")
        return False


def show_json_structure():
    """Mostra a estrutura JSON que será enviada ao frontend."""
    
    print("\n" + "=" * 80)
    print("ESTRUTURA JSON PARA FRONTEND")
    print("=" * 80)
    
    # Simular estrutura que seria passada ao template
    rep_section = PetitionSection.query.filter_by(slug="representante-legal").first()
    
    if rep_section:
        structure = {
            "section": {
                "id": rep_section.id,
                "name": rep_section.name,
                "slug": rep_section.slug,
                "description": rep_section.description,
                "icon": rep_section.icon,
                "color": rep_section.color,
                "fields_schema": rep_section.fields_schema or [],
            },
            "is_required": False,
            "is_expanded": False,
            "field_overrides": {},
            "is_linked_section": True,
        }
        
        print("\nSecao de Representante Legal (JSON):")
        print(json.dumps(structure, indent=2, ensure_ascii=False))
    
    # Mostrar exemplo de campo cpf_cnpj
    autor_section = PetitionSection.query.filter_by(slug="autor").first()
    if autor_section:
        for field in (autor_section.fields_schema or []):
            if field.get("type") == "cpf_cnpj":
                print(f"\nCampo CPF/CNPJ (autor_cpf):")
                print(json.dumps(field, indent=2, ensure_ascii=False))
                break


def main():
    """Função principal."""
    
    app = create_app()
    
    with app.app_context():
        is_valid = validate_implementation()
        show_json_structure()
        
        print("\n" + "=" * 80)
        if is_valid:
            print("IMPLEMENTACAO PRONTA PARA USO!")
        else:
            print("CORRIGIR ERROS ANTES DE USAR")
        print("=" * 80)


if __name__ == "__main__":
    main()
