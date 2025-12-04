import psycopg2

conn = psycopg2.connect(
    host="db.wnagrszaulrlbmhzapye.supabase.co",
    port=6543,
    database="postgres",
    user="postgres",
    password="@Y8&9XKj63y6jpL",
    sslmode="require",
)
cur = conn.cursor()

tables = [
    "user",
    "billing_plans",
    "petition_types",
    "petition_templates",
    "estados",
    "cidades",
    "user_plans",
    "petition_usage",
]

for table in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        count = cur.fetchone()[0]
        print(f"  {table}: {count} registros")
    except Exception as e:
        print(f"  {table}: ERRO - {e}")
        conn.rollback()

conn.close()
