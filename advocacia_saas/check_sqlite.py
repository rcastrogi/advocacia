import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tabelas no SQLite:")
for t in tables:
    name = t[0]
    if not name.startswith('sqlite') and not name.startswith('alembic'):
        count = cursor.execute(f"SELECT COUNT(*) FROM '{name}'").fetchone()[0]
        print(f"  - {name}: {count} registros")

conn.close()
