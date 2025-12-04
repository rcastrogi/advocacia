"""
Script para migrar tabelas restantes para o Supabase.
"""

import sqlite3
import psycopg2

SQLITE_PATH = 'instance/app.db'

# Conectar
print("Conectando...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

pg_conn = psycopg2.connect(
    host='db.wnagrszaulrlbmhzapye.supabase.co', 
    port=6543, 
    database='postgres', 
    user='postgres', 
    password='@Y8&9XKj63y6jpL', 
    sslmode='require'
)

# Tabelas para migrar
tables = ['petition_templates', 'petition_usage', 'user_plans']

BOOLEAN_FIELDS = {'is_active', 'active', 'is_admin', 'is_implemented', 
                  'is_billable', 'is_featured', 'is_approved', 'is_global',
                  'billable', 'is_current'}

def convert_value(key, value):
    if key in BOOLEAN_FIELDS and value is not None:
        return bool(value)
    return value

sqlite_cur = sqlite_conn.cursor()
pg_cur = pg_conn.cursor()

for table in tables:
    sqlite_cur.execute(f'SELECT * FROM "{table}"')
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f"  {table}: vazia")
        continue
    
    cols = [d[0] for d in sqlite_cur.description]
    print(f"  {table} ({len(rows)} registros)...", end=" ", flush=True)
    
    inserted = 0
    errors = 0
    
    for row in rows:
        try:
            values = [convert_value(cols[i], row[i]) for i in range(len(cols))]
            col_names = ', '.join([f'"{c}"' for c in cols])
            placeholders = ', '.join(['%s'] * len(cols))
            
            sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            pg_cur.execute(sql, values)
            inserted += 1
            
        except Exception as e:
            errors += 1
            pg_conn.rollback()
            if errors <= 2:
                print(f"\n    Erro: {str(e)[:100]}")
    
    pg_conn.commit()
    print(f"OK ({inserted})")
    
    # Atualizar sequence
    if 'id' in cols and inserted > 0:
        try:
            max_id = max(dict(zip(cols, r)).get('id', 0) or 0 for r in rows)
            if max_id:
                pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), %s, false)", (max_id + 1,))
                pg_conn.commit()
        except:
            pg_conn.rollback()

sqlite_conn.close()
pg_conn.close()

print("\n✓ Migração das tabelas restantes concluída!")
