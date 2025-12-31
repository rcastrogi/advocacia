#!/usr/bin/env python3
"""
Script seguro para limpeza de código legado - Petitio SaaS
Remove apenas arquivos confirmadamente obsoletos baseados no log de migração
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def safe_cleanup():
    """Remove arquivos legados de forma segura"""

    project_root = Path(__file__).parent

    # === ARQUIVOS CONFIRMAVELMENTE OBOSELETOS ===
    # Baseado no MIGRATION_LOG_20251223.md - migrações já aplicadas com sucesso

    confirmed_obsolete = [
        # Scripts de migração únicos já executados (23/12/2025)
        "add_cancellation_policy.py",  # ✅ Campos adicionados com sucesso
        "add_columns_manual.py",       # ✅ Colunas billing_plans adicionadas
        "migrate_remote.py",          # ✅ Migração para Render aplicada

        # Scripts de correção únicos (já executados)
        "fix_column.py",              # Correção de coluna petition_model_id
        "fix_nationality_column.py",  # Correção de coluna nationality
        "fix_fields_schema.py",       # Correção de schema de campos
        "fix_admin_access.py",        # Correção de acesso admin
        "fix_petition_models.py",     # Correção de modelos de petição
        "fix_remaining_models.py",    # Correção de modelos restantes

        # Scripts de criação únicos (já executados)
        "create_section_tables.py",   # Tabelas de seções criadas
        "create_petition_sections.py", # Seções de petição criadas
        "create_comprehensive_sections.py", # Seções abrangentes criadas
        "update_billing_plans.py",    # Planos de cobrança atualizados
        "update_plan_limits.py",      # Limites de planos atualizados

        # Scripts de demonstração temporários
        "demonstrate_roadmap_improvements.py", # Demonstração das melhorias
        "demonstrate_separation.py",   # Demonstração de separação

        # Scripts de verificação únicos (já utilizados)
        "check_admin_user.py",        # Verificação de usuário admin
        "check_migration.py",         # Verificação de migração
        "check_route.py",             # Verificação de rota
        "check_sections_page.py",     # Verificação de página de seções
        "check_tables.py",            # Verificação de tabelas
        "check_models.py",            # Verificação de modelos
        "check_process_tables.py",    # Verificação de tabelas de processo
    ]

    # === SCRIPTS DE TESTE TEMPORÁRIOS (mais recentes - avaliar com cuidado) ===
    # Estes podem ser mantidos por enquanto para debugging se necessário
    test_scripts_recent = [
        "test_admin_access.py",
        "test_admin_access_simple.py",
        "test_portal_logging.py",
        "test_run.py",
        "test_routes_advanced.py",
        "test_advanced.py",
        "test_processes_system.py",
        "test_notification_query.py",
        "test_dashboard_simple.py",
        "test_processes_route.py",
        "test_processes_simple.py",
        "test_processes_page.py",
        "test_imports_processes.py",
        "test_processes_manual.py",
        "test_server.py",
    ]

    print("🧹 INICIANDO LIMPEZA SEGURA DE CÓDIGO LEGADO")
    print(f"📅 Data/Hora: {datetime.now()}")
    print(f"📂 Diretório: {project_root}")
    print()

    # Backup dos arquivos antes de remover
    backup_dir = project_root / "backup_legacy_scripts"
    backup_dir.mkdir(exist_ok=True)

    removed_count = 0
    skipped_count = 0

    print("=== REMOVENDO ARQUIVOS CONFIRMAVELMENTE OBSOLETOS ===")

    for filename in confirmed_obsolete:
        file_path = project_root / filename

        if file_path.exists():
            # Fazer backup
            shutil.copy2(file_path, backup_dir / filename)

            # Remover arquivo
            file_path.unlink()
            print(f"✅ Removido: {filename}")
            removed_count += 1
        else:
            print(f"⚠️  Já removido: {filename}")
            skipped_count += 1

    print()
    print("=== RESUMO DA LIMPEZA ===")
    print(f"📦 Arquivos removidos: {removed_count}")
    print(f"⏭️  Arquivos já removidos: {skipped_count}")
    print(f"💾 Backup criado em: {backup_dir}")

    if removed_count > 0:
        print()
        print("📋 PRÓXIMOS PASSOS RECOMENDADOS:")
        print("1. Execute os testes: python run_tests.py")
        print("2. Verifique se a aplicação inicia: python run.py")
        print("3. Teste funcionalidades críticas (login, admin, petições)")
        print("4. Se tudo OK, considere remover scripts de teste temporários")

    print()
    print("🛡️  SCRIPTS DE TESTE RECENTES MANTIDOS (avaliar separadamente):")
    for script in test_scripts_recent[:5]:  # Mostra apenas os primeiros 5
        print(f"   - {script}")
    if len(test_scripts_recent) > 5:
        print(f"   ... e mais {len(test_scripts_recent) - 5} arquivos")

    print()
    print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")


if __name__ == "__main__":
    safe_cleanup()