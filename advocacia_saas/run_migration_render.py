#!/usr/bin/env python3
"""
Script para executar a migração SQL no Render
"""

import os

from app import create_app, db
from sqlalchemy import text


def run_migration():
    """Executa a migração SQL"""
    app = create_app()

    with app.app_context():
        # Ler o arquivo SQL
        sql_file = os.path.join(os.path.dirname(__file__), "..", "migration_render.sql")
        if not os.path.exists(sql_file):
            print(f"Arquivo {sql_file} não encontrado!")
            return

        with open(sql_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Dividir em statements (CREATE TABLE separados)
        statements = [
            stmt.strip()
            for stmt in sql_content.split(";")
            if stmt.strip() and not stmt.strip().startswith("--")
        ]

        print(f"Encontrados {len(statements)} statements SQL para executar.")

        # Executar cada statement
        for i, stmt in enumerate(statements, 1):
            try:
                print(f"Executando statement {i}/{len(statements)}...")
                db.session.execute(text(stmt))
                print(f"Statement {i} executado com sucesso.")
            except Exception as e:
                print(f"Erro no statement {i}: {e}")
                db.session.rollback()
                return

        db.session.commit()
        print("Migração concluída com sucesso!")


if __name__ == "__main__":
    run_migration()
