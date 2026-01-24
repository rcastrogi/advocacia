"""
RESET DE MIGRATIONS - Guia Passo a Passo
========================================

Este script guia o processo de reset das migrations, criando uma baseline
a partir do estado atual do banco de dados no Render.

IMPORTANTE: Execute cada passo cuidadosamente!
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# datetime removed - unused


def print_step(num, title):
    print(f"\n{'=' * 60}")
    print(f"PASSO {num}: {title}")
    print("=" * 60)


def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           RESET DE MIGRATIONS - PETITIO                         ║
║                                                                  ║
║  Este processo vai:                                              ║
║  1. Fazer backup das migrations atuais                          ║
║  2. Deletar todas as migrations antigas                         ║
║  3. Criar uma migration baseline do estado atual                ║
║  4. Atualizar o alembic_version no banco                        ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    print_step(1, "BACKUP DAS MIGRATIONS ATUAIS")
    print("""
Execute no terminal:

    cd F:\\PROJETOS\\advocacia\\advocacia_saas
    mkdir migrations_backup
    Copy-Item migrations\\versions\\*.py migrations_backup\\
    
Isso cria um backup de segurança.
""")

    print_step(2, "DELETAR MIGRATIONS ANTIGAS")
    print("""
Execute no terminal:

    cd F:\\PROJETOS\\advocacia\\advocacia_saas\\migrations\\versions
    Remove-Item *.py
    Remove-Item __pycache__ -Recurse -Force
    
Isso remove todas as migrations antigas.
""")

    print_step(3, "CRIAR MIGRATION BASELINE")
    print("""
Execute no terminal:

    cd F:\\PROJETOS\\advocacia\\advocacia_saas
    python -m flask db revision --autogenerate -m "baseline_from_render"
    
Isso cria uma migration com TODO o schema atual dos models.

IMPORTANTE: Edite a migration gerada e adicione no TOPO do upgrade():

    # Não criar tabelas que já existem no Render
    from sqlalchemy import inspect
    inspector = inspect(op.get_bind())
    existing_tables = inspector.get_table_names()
    
E em cada op.create_table(), adicione verificação:

    if 'nome_tabela' not in existing_tables:
        op.create_table(...)
""")

    print_step(4, "ATUALIZAR ALEMBIC_VERSION NO BANCO")
    print("""
Após criar a migration baseline, você precisa registrar ela no banco
SEM executar (porque as tabelas já existem).

Primeiro, veja o ID da nova migration (nome do arquivo, ex: abc123_baseline.py)

Depois execute:

    python scripts/recreate_migrations.py --apply abc123
    
Substitua 'abc123' pelo ID real da sua migration.
""")

    print_step(5, "TESTAR")
    print("""
Para verificar se está tudo ok:

    python -m flask db current
    python -m flask db heads
    
Ambos devem mostrar o mesmo ID.
""")

    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    PROCESSO CONCLUÍDO                           ║
║                                                                  ║
║  A partir de agora, novas migrations funcionarão normalmente!   ║
║  Use: flask db revision --autogenerate -m "descricao"           ║
╚══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
