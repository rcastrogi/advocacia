#!/usr/bin/env python3
"""
Script de limpeza do projeto Petitio SaaS
Remove arquivos temporários e cache
"""

import os
import shutil
from pathlib import Path


def cleanup_project():
    """Remove arquivos desnecessários"""

    project_root = Path(__file__).parent

    # Arquivos a remover
    files_to_remove = [
        # Scripts temporários
        "add_color_column.py",
        "add_is_active_column.py",
        "add_mle_template.py",
        "add_penhora_inss_template.py",
        "add_petition_limit_column.py",
        "migrate_direct.py",
        "migrate_password_security.py",
        "migrate_remaining.py",
        "migrate_simple.py",
        "migrate_to_supabase.py",
        "migrate_render.sh",
        "check_examples.py",
        "check_petition.py",
        "check_sqlite.py",
        "check_supabase.py",
        "demonstrate_legal_policy.py",
        "demonstrate_policy.py",
        "demonstrate_system.py",
        "create_petition_examples.py",
        "create_real_case_examples.py",
        "create_real_case_templates.py",
        "create_sample_petition_type.py",
        "create_sample_template.py",
        "create_test_client.py",
        "run_examples_manual.py",
        "run_examples_render.sh",
        "check_status.bat",
        "deploy.bat",
        "deploy.ps1",
        "app.db",
        "populate_basic_sections.py",
        "populate_locations.py",
        "setup_petition_sections.py",
        "setup_saved_petitions.py",
        "setup_sections_simple.py",
        "setup_sections_v2.py",
    ]

    removed_count = 0
    total_size = 0

    print("🧹 Iniciando limpeza do projeto...")

    # Remover arquivos específicos
    for file in files_to_remove:
        file_path = project_root / file
        if file_path.exists():
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                print(f"✅ Removido: {file} ({size:,} bytes)")
                removed_count += 1
                total_size += size
            except Exception as e:
                print(f"❌ Erro ao remover {file}: {e}")

    # Remover arquivos de cache
    cache_removed = 0
    cache_size = 0

    for pattern in ["**/__pycache__", "**/*.pyc", "**/*.pyo"]:
        for cache_file in project_root.glob(pattern):
            try:
                if cache_file.is_file():
                    size = cache_file.stat().st_size
                    cache_file.unlink()
                    cache_size += size
                elif cache_file.is_dir():
                    shutil.rmtree(cache_file)
                cache_removed += 1
            except Exception as e:
                print(f"❌ Erro ao remover cache {cache_file}: {e}")

    print(f"\n📊 RESUMO DA LIMPEZA:")
    print(f"  - Arquivos removidos: {removed_count}")
    print(f"  - Arquivos de cache: {cache_removed}")
    print(f"  - Espaço liberado: {total_size + cache_size:,} bytes")
    print("\n✅ Limpeza concluída!")


if __name__ == "__main__":
    cleanup_project()
