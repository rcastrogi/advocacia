#!/usr/bin/env python3
"""
Script para listar tipos dinâmicos restantes e migrar um por vez
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import PetitionModel, PetitionType
from sqlalchemy import text


def list_remaining_types():
    """Lista tipos dinâmicos que ainda não foram migrados"""
    app = create_app()
    with app.app_context():
        # Busca tipos dinâmicos
        dynamic_types = PetitionType.query.filter(
            PetitionType.type_sections.any()
        ).all()

        print(f"📊 Encontrados {len(dynamic_types)} tipos dinâmicos")
        print("\n=== TIPOS DINÂMICOS ===")

        remaining = []
        for pt in dynamic_types:
            # Verifica se já foi migrado
            existing_model = PetitionModel.query.filter_by(
                name=f"Modelo - {pt.name}", petition_type_id=pt.id
            ).first()

            if existing_model:
                print(f"✅ {pt.name} (ID: {pt.id}) - Já migrado")
            else:
                print(f"⏳ {pt.name} (ID: {pt.id}) - Pendente")
                remaining.append(pt.id)

        print(f"\n🔄 Tipos pendentes: {len(remaining)}")
        if remaining:
            print("IDs pendentes:", remaining)

        return remaining


def migrate_next_type():
    """Migra o próximo tipo pendente"""
    remaining = list_remaining_types()
    if not remaining:
        print("🎉 Todos os tipos já foram migrados!")
        return True

    next_type_id = remaining[0]
    print(f"\n🔄 Migrando próximo tipo (ID: {next_type_id})...")

    # Executa o script de migração single
    import subprocess

    result = subprocess.run(
        [sys.executable, "migrate_single.py", str(next_type_id)],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--migrate":
        success = migrate_next_type()
        sys.exit(0 if success else 1)
    else:
        list_remaining_types()
