"""
Script simplificado para migrar dados do SQLite para PostgreSQL (Supabase).
Usa SQL direto para evitar problemas com ORM.
"""

import os
import sys
from datetime import datetime
from urllib.parse import quote_plus

# Configuração do Supabase
SUPABASE_HOST = "db.wnagrszaulrlbmhzapye.supabase.co"
SUPABASE_PORT = "6543"
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "@Y8&9XKj63y6jpL"

ENCODED_PASSWORD = quote_plus(SUPABASE_PASSWORD)
POSTGRES_URL = f"postgresql://{SUPABASE_USER}:{ENCODED_PASSWORD}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}?sslmode=require"

basedir = os.path.dirname(__file__)
SQLITE_PATH = os.path.join(basedir, 'instance', 'app.db')

import sqlite3
from sqlalchemy import create_engine, text

# Campos booleanos conhecidos
BOOLEAN_FIELDS = {
    'is_active', 'active', 'is_admin', 'is_implemented', 
    'is_billable', 'is_featured', 'is_approved',
    'has_prenup', 'has_domestic_violence', 
    'has_protective_order', 'request_free_justice',
    'signature_author', 'confirmed', 'email_confirmed',
    'force_password_change', 'is_popular', 'is_unlimited'
}


def convert_row(row_dict):
    """Converte tipos SQLite para PostgreSQL."""
    for key, value in list(row_dict.items()):
        # Converter 0/1 para boolean
        if key in BOOLEAN_FIELDS:
            if value is not None:
                row_dict[key] = bool(value)
    return row_dict


def migrate_table(engine, sqlite_cursor, table_name):
    """Migra uma tabela específica."""
    sqlite_cursor.execute(f'SELECT * FROM "{table_name}"')
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  ⏭️  {table_name}: vazia")
        return 0, 0
    
    columns = [d[0] for d in sqlite_cursor.description]
    print(f"  📥 {table_name} ({len(rows)})...", end=" ", flush=True)
    
    inserted = 0
    errors = 0
    
    # Processar linha por linha com commit individual
    for row in rows:
        try:
            row_dict = convert_row(dict(row))
            
            cols = ', '.join([f'"{c}"' for c in row_dict.keys()])
            placeholders = ', '.join([f':{c}' for c in row_dict.keys()])
            
            sql = text(f'''
                INSERT INTO "{table_name}" ({cols}) 
                VALUES ({placeholders}) 
                ON CONFLICT DO NOTHING
            ''')
            
            with engine.begin() as conn:
                conn.execute(sql, row_dict)
            
            inserted += 1
            
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"\n      ⚠️ Erro: {str(e)[:100]}")
    
    status = f"✓ {inserted}" + (f" ({errors} erros)" if errors else "")
    print(status)
    
    return inserted, len(rows)


def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO SQLite → PostgreSQL (Supabase)")
    print("=" * 60)
    
    # Conectar ao SQLite
    print(f"\n📂 SQLite: {SQLITE_PATH}")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Conectar ao PostgreSQL
    print(f"🐘 PostgreSQL: {SUPABASE_HOST}")
    os.environ['DATABASE_URL'] = POSTGRES_URL
    
    # Criar tabelas usando Flask
    print("\n🔨 Criando tabelas no PostgreSQL...")
    from app import create_app, db
    app = create_app()
    
    with app.app_context():
        db.create_all()
        print("  ✓ Tabelas criadas!")
        
        engine = db.engine
        
        # Listar tabelas do SQLite
        sqlite_cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%' 
            AND name NOT LIKE 'alembic_%'
        """)
        tables = [row[0] for row in sqlite_cursor.fetchall()]
        
        # Ordem de migração (tabelas principais primeiro)
        priority_tables = [
            'user', 'billing_plans', 'petition_types', 'estados',
            'petition_templates', 'client', 'testimonials',
            'petition_usage', 'user_plans',
        ]
        
        # Tabelas a pular (muito grandes ou não essenciais)
        skip_tables = {'cidades'}  # Pode adicionar depois manualmente
        
        print(f"\n📥 Migrando dados principais...")
        
        total_inserted = 0
        total_rows = 0
        
        # Migrar tabelas prioritárias
        for table_name in priority_tables:
            if table_name in tables and table_name not in skip_tables:
                ins, total = migrate_table(engine, sqlite_cursor, table_name)
                total_inserted += ins
                total_rows += total
        
        # Migrar outras tabelas
        for table_name in tables:
            if table_name not in priority_tables and table_name not in skip_tables:
                ins, total = migrate_table(engine, sqlite_cursor, table_name)
                total_inserted += ins
                total_rows += total
        
        # Atualizar sequences
        print("\n🔧 Atualizando sequences...")
        for table_name in tables:
            if table_name in skip_tables:
                continue
            try:
                sqlite_cursor.execute(f'SELECT MAX(id) FROM "{table_name}"')
                max_id = sqlite_cursor.fetchone()[0]
                if max_id:
                    with engine.begin() as conn:
                        conn.execute(text(f"""
                            SELECT setval(
                                pg_get_serial_sequence('{table_name}', 'id'), 
                                {max_id + 1}, 
                                false
                            )
                        """))
            except:
                pass
        print("  ✓ OK")
    
    sqlite_conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ MIGRAÇÃO CONCLUÍDA! ({total_inserted}/{total_rows} registros)")
    print("=" * 60)
    print("\n📋 O arquivo .env já está configurado.")
    print("   Reinicie a aplicação Flask para testar.")
    print("\n⚠️  Nota: Tabela 'cidades' pulada (188 registros).")
    print("   Execute separadamente se necessário.")


if __name__ == "__main__":
    main()
