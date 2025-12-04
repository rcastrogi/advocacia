"""
Script para migrar dados do SQLite para PostgreSQL (Supabase).
"""

import os
import sys
from datetime import datetime
from urllib.parse import quote_plus

# Configuração do Supabase
SUPABASE_HOST = "db.wnagrszaulrlbmhzapye.supabase.co"
SUPABASE_PORT = "6543"  # Porta do connection pooler (mais estável)
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres"
SUPABASE_PASSWORD = "@Y8&9XKj63y6jpL"

# Codificar a senha para URL (caracteres especiais)
ENCODED_PASSWORD = quote_plus(SUPABASE_PASSWORD)
POSTGRES_URL = f"postgresql://{SUPABASE_USER}:{ENCODED_PASSWORD}@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}?sslmode=require"

print(f"URL: postgresql://{SUPABASE_USER}:****@{SUPABASE_HOST}:{SUPABASE_PORT}/{SUPABASE_DB}")

# Caminho do banco SQLite - verificar em instance/ primeiro
basedir = os.path.dirname(__file__)
SQLITE_PATH = os.path.join(basedir, 'instance', 'app.db')
if not os.path.exists(SQLITE_PATH):
    SQLITE_PATH = os.path.join(basedir, 'app.db')

from sqlalchemy import create_engine, text
import sqlite3


def get_sqlite_tables_and_data():
    """Extrai todos os dados do SQLite."""
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Obter lista de tabelas (excluindo as do sistema)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%' 
        AND name NOT LIKE 'alembic_%'
        ORDER BY name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    data = {}
    for table in tables:
        try:
            cursor.execute(f'SELECT * FROM "{table}"')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            data[table] = {
                'columns': columns,
                'rows': [dict(row) for row in rows]
            }
            print(f"  📦 {table}: {len(rows)} registros")
        except Exception as e:
            print(f"  ⚠️  Erro ao ler {table}: {e}")
    
    conn.close()
    return data


def test_connection(engine):
    """Testa a conexão com o PostgreSQL."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"  ✓ Conectado: PostgreSQL {version.split(',')[0].replace('PostgreSQL ', '')}")
            return True
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")
        return False


def migrate_using_flask_models(sqlite_data):
    """Migra os dados usando os modelos do Flask para garantir compatibilidade."""
    
    # Configurar a URL do PostgreSQL no ambiente
    os.environ['DATABASE_URL'] = POSTGRES_URL
    
    from app import create_app, db
    from app.models import (
        User, Client, Dependent, PetitionType, PetitionTemplate,
        BillingPlan, UserPlan, Payment, PetitionUsage, Invoice,
        Testimonial, Estado, Cidade
    )
    
    app = create_app()
    
    with app.app_context():
        print("\n🔨 Criando tabelas no PostgreSQL...")
        db.create_all()
        print("  ✓ Tabelas criadas!")
        
        # Mapeamento: nome da tabela SQLite -> (modelo, campos especiais)
        table_mapping = {
            'user': (User, {}),
            'billing_plans': (BillingPlan, {}),
            'petition_types': (PetitionType, {}),
            'petition_templates': (PetitionTemplate, {}),
            'client': (Client, {}),
            'dependent': (Dependent, {}),
            'estados': (Estado, {}),
            'cidades': (Cidade, {}),
            'testimonials': (Testimonial, {}),
            'petition_usage': (PetitionUsage, {}),
            'payments': (Payment, {}),
            'invoices': (Invoice, {}),
            'user_plans': (UserPlan, {}),
        }
        
        # Ordem de inserção (respeitando foreign keys)
        insert_order = [
            'user',
            'billing_plans',
            'petition_types',
            'estados',
            'cidades',
            'petition_templates',
            'client',
            'dependent',
            'testimonials',
            'petition_usage',
            'invoices',
            'payments',
            'user_plans',
        ]
        
        print(f"\n📥 Migrando dados...")
        
        for table_name in insert_order:
            if table_name not in sqlite_data:
                continue
            
            if table_name not in table_mapping:
                print(f"  ⏭️  {table_name}: não mapeado")
                continue
            
            model, special_fields = table_mapping[table_name]
            rows = sqlite_data[table_name]['rows']
            
            if not rows:
                print(f"  ⏭️  {table_name}: vazia")
                continue
            
            print(f"  📥 {table_name}...", end=" ", flush=True)
            
            inserted = 0
            errors = 0
            
            for row in rows:
                try:
                    # Filtrar apenas colunas válidas do modelo
                    valid_columns = {c.name for c in model.__table__.columns}
                    clean_row = {}
                    
                    for key, value in row.items():
                        if key not in valid_columns:
                            continue
                        
                        # Converter datas
                        if value and isinstance(value, str):
                            if key.endswith('_at') or key.endswith('_date') or 'date' in key.lower():
                                try:
                                    # Tentar vários formatos
                                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                        try:
                                            clean_row[key] = datetime.strptime(value, fmt)
                                            break
                                        except ValueError:
                                            continue
                                    else:
                                        clean_row[key] = value
                                except:
                                    clean_row[key] = value
                            else:
                                clean_row[key] = value
                        else:
                            clean_row[key] = value
                    
                    # Criar e adicionar objeto
                    obj = model(**clean_row)
                    db.session.merge(obj)
                    inserted += 1
                    
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        print(f"\n      ⚠️ {str(e)[:60]}")
            
            try:
                db.session.commit()
                print(f"✓ {inserted} registros" + (f" ({errors} erros)" if errors else ""))
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro: {str(e)[:50]}")
        
        # Migrar tabelas de associação
        print("\n📥 Migrando tabelas de associação...")
        
        # user_plans
        if 'user_plans' in sqlite_data:
            rows = sqlite_data['user_plans']['rows']
            if rows:
                print(f"  📥 user_plans...", end=" ", flush=True)
                for row in rows:
                    try:
                        db.session.execute(text(
                            "INSERT INTO user_plans (user_id, plan_id) VALUES (:user_id, :plan_id) ON CONFLICT DO NOTHING"
                        ), row)
                    except:
                        pass
                db.session.commit()
                print(f"✓ {len(rows)} registros")
        
        # plan_petition_types
        if 'plan_petition_types' in sqlite_data:
            rows = sqlite_data['plan_petition_types']['rows']
            if rows:
                print(f"  📥 plan_petition_types...", end=" ", flush=True)
                for row in rows:
                    try:
                        db.session.execute(text(
                            "INSERT INTO plan_petition_types (plan_id, petition_type_id) VALUES (:plan_id, :petition_type_id) ON CONFLICT DO NOTHING"
                        ), row)
                    except:
                        pass
                db.session.commit()
                print(f"✓ {len(rows)} registros")
        
        print("\n🔧 Atualizando sequences...")
        # Atualizar sequences para evitar conflitos de ID
        for table_name in insert_order:
            if table_name in sqlite_data and sqlite_data[table_name]['rows']:
                rows = sqlite_data[table_name]['rows']
                max_id = max((r.get('id', 0) or 0) for r in rows)
                if max_id > 0:
                    try:
                        pg_table = table_mapping.get(table_name, (None, {}))[0]
                        if pg_table:
                            actual_table_name = pg_table.__tablename__
                            db.session.execute(text(f"""
                                SELECT setval(pg_get_serial_sequence('{actual_table_name}', 'id'), {max_id + 1}, false)
                            """))
                    except:
                        pass
        db.session.commit()
        print("  ✓ Sequences atualizadas!")


def main():
    print("=" * 60)
    print("🚀 MIGRAÇÃO SQLite → PostgreSQL (Supabase)")
    print("=" * 60)
    
    # Verificar se SQLite existe
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ Banco SQLite não encontrado: {SQLITE_PATH}")
        sys.exit(1)
    
    print(f"\n📂 SQLite: {SQLITE_PATH}")
    print(f"🐘 PostgreSQL: {SUPABASE_HOST}")
    
    # Criar engine PostgreSQL para teste
    engine = create_engine(POSTGRES_URL, echo=False)
    
    # Testar conexão
    print("\n🔌 Testando conexão com Supabase...")
    if not test_connection(engine):
        sys.exit(1)
    
    # Extrair dados do SQLite
    print("\n📤 Extraindo dados do SQLite...")
    sqlite_data = get_sqlite_tables_and_data()
    
    # Migrar dados usando os modelos Flask
    migrate_using_flask_models(sqlite_data)
    
    print("\n" + "=" * 60)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    print("\n📋 Próximos passos:")
    print("   1. O arquivo .env já está configurado com DATABASE_URL")
    print("   2. Reinicie a aplicação Flask")
    print("   3. Teste o login e funcionalidades")


if __name__ == "__main__":
    main()
