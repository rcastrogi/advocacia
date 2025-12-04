"""
Script de migração SQLite → PostgreSQL usando psycopg2 diretamente.
"""

import sqlite3
from urllib.parse import quote_plus

import psycopg2
from psycopg2.extras import execute_values

# Configuração
SQLITE_PATH = "instance/app.db"

SUPABASE_HOST = "db.wnagrszaulrlbmhzapye.supabase.co"
SUPABASE_PORT = 6543
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "@Y8&9XKj63y6jpL"

# Campos booleanos
BOOLEAN_FIELDS = {
    "is_active",
    "active",
    "is_admin",
    "is_implemented",
    "is_billable",
    "is_featured",
    "is_approved",
    "has_prenup",
    "has_domestic_violence",
    "has_protective_order",
    "request_free_justice",
    "signature_author",
    "confirmed",
    "email_confirmed",
    "force_password_change",
    "is_popular",
    "is_unlimited",
}


def convert_value(key, value):
    if key in BOOLEAN_FIELDS and value is not None:
        return bool(value)
    return value


def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO SQLite → PostgreSQL (Supabase)")
    print("=" * 60)

    # Conectar SQLite
    print(f"\n📂 Conectando SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    # Conectar PostgreSQL
    print(f"🐘 Conectando PostgreSQL: {SUPABASE_HOST}")
    pg_conn = psycopg2.connect(
        host=SUPABASE_HOST,
        port=SUPABASE_PORT,
        database=SUPABASE_DB,
        user=SUPABASE_USER,
        password=SUPABASE_PASSWORD,
        sslmode="require",
        connect_timeout=30,
    )
    pg_conn.autocommit = False
    print("  ✓ Conectado!")

    # Criar tabelas primeiro (precisa do Flask)
    print("\n🔨 Criando tabelas...")
    import os

    os.environ["DATABASE_URL"] = (
        f"postgresql://{SUPABASE_USER}:{quote_plus(SUPABASE_PASSWORD)}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}?sslmode=require"
    )

    from app import create_app, db

    app = create_app()
    with app.app_context():
        db.create_all()
    print("  ✓ Tabelas criadas!")

    # Listar tabelas SQLite
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%' 
        AND name NOT LIKE 'alembic_%'
    """)
    tables = [r[0] for r in sqlite_cur.fetchall()]

    # Ordem de migração
    priority = [
        "user",
        "billing_plans",
        "petition_types",
        "estados",
        "petition_templates",
        "client",
        "testimonials",
        "petition_usage",
        "user_plans",
    ]

    skip = {"cidades"}  # Pular tabelas grandes por enquanto

    ordered = [t for t in priority if t in tables]
    ordered += [t for t in tables if t not in priority and t not in skip]

    print(f"\n📥 Migrando {len(ordered)} tabelas...")

    pg_cur = pg_conn.cursor()
    total_inserted = 0

    for table in ordered:
        # Ler dados SQLite
        sqlite_cur.execute(f'SELECT * FROM "{table}"')
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"  ⏭️  {table}: vazia")
            continue

        cols = [d[0] for d in sqlite_cur.description]
        print(f"  📥 {table} ({len(rows)})...", end=" ", flush=True)

        inserted = 0
        errors = 0

        for row in rows:
            try:
                # Converter valores
                values = [convert_value(cols[i], row[i]) for i in range(len(cols))]

                # Montar INSERT
                col_names = ", ".join([f'"{c}"' for c in cols])
                placeholders = ", ".join(["%s"] * len(cols))

                sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

                pg_cur.execute(sql, values)
                inserted += 1

            except Exception as e:
                errors += 1
                pg_conn.rollback()
                if errors <= 2:
                    print(f"\n      ⚠️ {str(e)[:80]}")

        pg_conn.commit()
        total_inserted += inserted

        status = f"✓ {inserted}" + (f" ({errors} erros)" if errors else "")
        print(status)

        # Atualizar sequence
        if "id" in cols and inserted > 0:
            try:
                max_id = max(dict(zip(cols, r)).get("id", 0) or 0 for r in rows)
                if max_id:
                    pg_cur.execute(
                        f"""
                        SELECT setval(pg_get_serial_sequence('{table}', 'id'), %s, false)
                    """,
                        (max_id + 1,),
                    )
                    pg_conn.commit()
            except:
                pg_conn.rollback()

    # Fechar conexões
    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "=" * 60)
    print(f"✅ MIGRAÇÃO CONCLUÍDA! ({total_inserted} registros)")
    print("=" * 60)
    print("\n📋 Reinicie a aplicação Flask para testar.")


if __name__ == "__main__":
    main()
