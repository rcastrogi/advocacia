#!/usr/bin/env python3
"""
Script para aplicar migração incremental no Render
Adiciona colunas faltantes às tabelas existentes
"""

import json
import os

from app import create_app, db
from sqlalchemy import inspect, text

# PostgreSQL reserved words that might conflict
RESERVED_WORDS = {
    "order",
    "group",
    "user",
    "table",
    "column",
    "select",
    "insert",
    "update",
    "delete",
    "create",
    "drop",
    "alter",
    "index",
    "primary",
    "foreign",
    "key",
    "null",
    "not",
    "and",
    "or",
    "like",
    "in",
    "exists",
    "between",
    "case",
    "when",
    "then",
    "else",
    "end",
    "from",
    "where",
    "join",
    "on",
    "having",
    "limit",
    "offset",
}


def quote_identifier(name):
    """Quote identifier if it's a reserved word"""
    if name.lower() in RESERVED_WORDS:
        return f'"{name}"'
    return name


def apply_incremental_migration():
    """Aplica migração incremental: adiciona colunas faltantes"""
    app = create_app()

    with app.app_context():
        # Carregar schema target
        schema_file = os.path.join(
            os.path.dirname(__file__), "..", "schema_render.json"
        )
        if not os.path.exists(schema_file):
            print(f"Arquivo {schema_file} não encontrado!")
            return

        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)

        inspector = inspect(db.engine)

        tables = schema["tables"]
        changes_made = 0

        for table_name, table_info in tables.items():
            if not inspector.has_table(table_name):
                print(f"Tabela {table_name} não existe - pulando (use CREATE primeiro)")
                continue

            # Verificar colunas existentes
            existing_columns = {
                col["name"]: col for col in inspector.get_columns(table_name)
            }

            for col in table_info["columns"]:
                col_name = col["name"]
                if col_name not in existing_columns:
                    # Coluna faltando - adicionar
                    col_type = col["type"]
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    default = f" DEFAULT {col['default']}" if col["default"] else ""
                    primary_key = " PRIMARY KEY" if col["primary_key"] else ""

                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {quote_identifier(col_name)} {col_type} {nullable}{default}{primary_key}"
                    try:
                        print(
                            f"Adicionando coluna {quote_identifier(col_name)} à tabela {table_name}..."
                        )
                        db.session.execute(text(alter_sql))
                        changes_made += 1
                    except Exception as e:
                        print(f"Erro ao adicionar coluna {col_name}: {e}")
                        db.session.rollback()
                        continue
                else:
                    # Coluna existe - verificar diferenças (básico)
                    existing = existing_columns[col_name]
                    # Aqui poderia verificar tipo, nullable, etc., mas simplificado
                    pass

        db.session.commit()
        print(f"Migração incremental concluída. {changes_made} alterações aplicadas.")


if __name__ == "__main__":
    apply_incremental_migration()
