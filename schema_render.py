#!/usr/bin/env python3
"""
Script para extrair a estrutura (schema) das tabelas do banco PostgreSQL do Render.
Salva em SQL para análise e comparação local.
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "advocacia_saas")
sys.path.insert(0, project_root)

from app import create_app, db


def export_schema():
    """Extrai o schema das tabelas usando SQLAlchemy"""
    print("🔍 Extraindo schema das tabelas...")

    # Usar SQLAlchemy para introspecção
    from sqlalchemy import inspect

    inspector = inspect(db.engine)

    schema_info = {
        "exported_at": datetime.now().isoformat(),
        "database_type": "postgresql_render",
        "tables": {},
    }

    # Pegar todas as tabelas
    tables = inspector.get_table_names()

    for table_name in tables:
        print(f"  📋 Analisando tabela: {table_name}")

        # Get primary key constraint
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = (
            set(pk_constraint.get("constrained_columns", []))
            if pk_constraint
            else set()
        )

        # Colunas
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append(
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col["default"] else None,
                    "primary_key": col["name"] in pk_columns,
                }
            )

        # Índices
        indexes = []
        for idx in inspector.get_indexes(table_name):
            indexes.append(
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx["unique"],
                }
            )

        # Foreign Keys
        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            fks.append(
                {
                    "name": fk["name"],
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
            )

        schema_info["tables"][table_name] = {
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": fks,
        }

    return schema_info


def save_schema_to_file(schema_info):
    """Salva o schema em arquivo JSON"""
    filename = f"schema_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    import json

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(schema_info, f, indent=2, ensure_ascii=False)

    print(f"✅ Schema salvo em: {filename}")
    return filename


def generate_sql_dump():
    """Gera um dump SQL da estrutura"""
    print("💾 Gerando dump SQL...")

    # Usar pg_dump se disponível (PostgreSQL)
    import subprocess

    sql_filename = f"schema_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

    try:
        # Tentar pg_dump (se disponível no Render)
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url and "postgresql" in db_url:
            # Extrair parâmetros da URL
            # postgresql://user:pass@host:port/db
            url_parts = db_url.replace("postgresql://", "").split("@")
            if len(url_parts) == 2:
                user_pass = url_parts[0].split(":")
                host_port_db = url_parts[1].split("/")

                if len(user_pass) == 2 and len(host_port_db) == 2:
                    user = user_pass[0]
                    password = user_pass[1]
                    host_port = host_port_db[0].split(":")
                    host = host_port[0]
                    port = host_port[1] if len(host_port) > 1 else "5432"
                    database = host_port_db[1]

                    # Executar pg_dump para schema only
                    cmd = [
                        "pg_dump",
                        f"--host={host}",
                        f"--port={port}",
                        f"--username={user}",
                        f"--dbname={database}",
                        "--schema-only",
                        "--no-owner",
                        "--no-privileges",
                        f"--file={sql_filename}",
                    ]

                    # Setar senha via env
                    env = os.environ.copy()
                    env["PGPASSWORD"] = password

                    result = subprocess.run(
                        cmd, env=env, capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        print(f"✅ Dump SQL salvo em: {sql_filename}")
                        return sql_filename
                    else:
                        print(f"⚠️ pg_dump falhou: {result.stderr}")

    except Exception as e:
        print(f"⚠️ Não foi possível gerar dump SQL: {e}")

    return None


def main():
    """Função principal"""
    print("🚀 Iniciando extração de schema do Render...")

    # Criar app e contexto
    app = create_app()
    with app.app_context():
        try:
            # Extrair schema
            schema_info = export_schema()

            # Salvar em JSON
            json_file = save_schema_to_file(schema_info)

            # Tentar gerar SQL dump
            sql_file = generate_sql_dump()

            print("\n📊 Estatísticas do schema:")
            print(f"   Tabelas encontradas: {len(schema_info['tables'])}")

            print(f"\n📁 Arquivos gerados:")
            print(f"   JSON: {json_file}")
            if sql_file:
                print(f"   SQL: {sql_file}")

            print(f"\n💻 Baixe os arquivos e compare com a estrutura local!")

        except Exception as e:
            print(f"❌ Erro durante extração: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
