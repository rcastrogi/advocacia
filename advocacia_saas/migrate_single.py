#!/usr/bin/env python3
"""
Script para migrar um tipo específico por vez
"""

import os
import re
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json

from app import create_app, db
from app.models import PetitionModel, PetitionModelSection, PetitionType


def generate_slug(name):
    """Gera um slug único baseado no nome"""
    # Converte para minúsculas, remove acentos e caracteres especiais
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")

    # Garante que seja único
    base_slug = slug
    counter = 1
    while PetitionModel.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def migrate_single_type(type_id):
    """Migra um único tipo de petição"""
    app = create_app()
    with app.app_context():
        try:
            # Busca o tipo
            petition_type = PetitionType.query.get(type_id)
            if not petition_type:
                print(f"❌ Tipo {type_id} não encontrado")
                return False

            # Verifica se já foi migrado
            existing_model = PetitionModel.query.filter_by(
                name=f"Modelo - {petition_type.name}", petition_type_id=petition_type.id
            ).first()

            if existing_model:
                print(f"⚠️  Modelo para {petition_type.name} já existe")
                return True

            print(f"🔄 Migrando tipo: {petition_type.name} (ID: {type_id})")

            # Gera slug único
            model_name = f"Modelo - {petition_type.name}"
            slug = generate_slug(model_name)

            # Cria o modelo
            model = PetitionModel(
                name=model_name,
                slug=slug,
                description=f"Modelo padrão para {petition_type.name}",
                petition_type_id=petition_type.id,
                is_active=True,
            )
            db.session.add(model)
            db.session.commit()

            print(f"  ✅ Modelo criado com ID: {model.id} (slug: {slug})")

            # Migra as seções
            type_sections = petition_type.type_sections.all()
            if type_sections:
                print(f"  📋 Migrando {len(type_sections)} seções")

                for type_section in type_sections:
                    model_section = PetitionModelSection(
                        petition_model_id=model.id,
                        section_id=type_section.section_id,
                        order=type_section.order,
                        is_required=type_section.is_required,
                        field_overrides=type_section.field_overrides or {},
                    )
                    db.session.add(model_section)

                db.session.commit()
                print(f"✅ Tipo {petition_type.name} migrado com sucesso!")
                return True
            else:
                print(f"⚠️  Tipo {petition_type.name} não tem seções")
                return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao migrar tipo {type_id}: {str(e)}")
            return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python migrate_single.py <type_id>")
        sys.exit(1)

    type_id = int(sys.argv[1])
    success = migrate_single_type(type_id)
    sys.exit(0 if success else 1)
