"""
Script para recriar migrations a partir do estado atual do banco de dados.

Este script:
1. Exporta todas as tabelas existentes no banco Render
2. Gera SQL para criar uma migration baseline
3. Permite reiniciar o histórico de migrations

Uso:
    python recreate_migrations.py --export    # Exporta schema atual
    python recreate_migrations.py --apply     # Aplica a nova baseline no alembic_version
"""

import os
import sys

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

from app import create_app  # noqa: E402
from app.models import db  # noqa: E402


def get_all_tables():
    """Retorna todas as tabelas do banco (exceto alembic_version)"""
    result = db.session.execute(
        db.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name != 'alembic_version'
        ORDER BY table_name
    """)
    ).fetchall()
    return [r[0] for r in result]


def get_table_columns(table_name):
    """Retorna as colunas de uma tabela"""
    result = db.session.execute(
        db.text(f"""
        SELECT column_name, data_type, is_nullable, column_default, 
               character_maximum_length, numeric_precision
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    ).fetchall()
    return result


def get_table_constraints(table_name):
    """Retorna as constraints de uma tabela"""
    result = db.session.execute(
        db.text(f"""
        SELECT tc.constraint_name, tc.constraint_type, kcu.column_name,
               ccu.table_name AS foreign_table_name, ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        LEFT JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        LEFT JOIN information_schema.constraint_column_usage AS ccu
            ON tc.constraint_name = ccu.constraint_name AND tc.constraint_type = 'FOREIGN KEY'
        WHERE tc.table_name = '{table_name}'
    """)
    ).fetchall()
    return result


def get_indexes(table_name):
    """Retorna os índices de uma tabela"""
    result = db.session.execute(
        db.text(f"""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = '{table_name}'
        AND indexname NOT LIKE '%_pkey'
    """)
    ).fetchall()
    return result


def export_schema():
    """Exporta o schema completo do banco"""
    tables = get_all_tables()

    print("=" * 70)
    print("SCHEMA ATUAL DO BANCO DE DADOS - RENDER")
    print("=" * 70)
    print(f"\nTotal de tabelas: {len(tables)}\n")

    for table in tables:
        print(f"\n{'=' * 50}")
        print(f"TABELA: {table}")
        print(f"{'=' * 50}")

        # Colunas
        columns = get_table_columns(table)
        print("\nColunas:")
        for col in columns:
            col_name, data_type, nullable, default, max_len, precision = col
            type_str = data_type
            if max_len:
                type_str += f"({max_len})"
            elif precision:
                type_str += f"({precision})"
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            print(f"  - {col_name}: {type_str} {null_str}{default_str}")

        # Índices
        indexes = get_indexes(table)
        if indexes:
            print("\nIndices:")
            for idx in indexes:
                print(f"  - {idx[0]}")

    print("\n" + "=" * 70)
    print("FIM DO EXPORT")
    print("=" * 70)

    return tables


def update_alembic_version(new_version):
    """Atualiza a versão do alembic no banco"""
    db.session.execute(db.text("DELETE FROM alembic_version"))
    db.session.execute(
        db.text(f"INSERT INTO alembic_version (version_num) VALUES ('{new_version}')")
    )
    db.session.commit()
    print(f"[OK] Alembic version atualizado para: {new_version}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Gerenciar migrations")
    parser.add_argument("--export", action="store_true", help="Exporta schema atual")
    parser.add_argument(
        "--apply", type=str, help="Aplica nova versao no alembic_version"
    )
    parser.add_argument(
        "--list-tables", action="store_true", help="Lista apenas nomes das tabelas"
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.export:
            export_schema()
        elif args.apply:
            update_alembic_version(args.apply)
        elif args.list_tables:
            tables = get_all_tables()
            print(f"Tabelas no banco ({len(tables)}):")
            for t in tables:
                print(f"  - {t}")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
