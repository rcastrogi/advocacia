#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rápido para corrigir o Render PostgreSQL
"""

import psycopg2

DATABASE_URL = 'postgresql://petitio_db_user:krGWlyjOxEJKLwgoNHBZjOzaMV1T0JZf@dpg-d54kpj6r433s73d37900-a.oregon-postgres.render.com/petitio_db'

def fix_render():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        print("\n" + "="*60)
        print("🔗 Conectado ao Render PostgreSQL")
        print("="*60)

        # Adicionar votes_per_period em billing_plans
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='billing_plans' AND column_name='votes_per_period'
        """)
        
        if not cursor.fetchone():
            print("⚠️  Adicionando votes_per_period em billing_plans...")
            cursor.execute("""
                ALTER TABLE billing_plans ADD COLUMN votes_per_period INTEGER DEFAULT 0
            """)
            print("✅ votes_per_period adicionado")
        else:
            print("✅ votes_per_period já existe")

        # Adicionar impact_score e effort_score em roadmap_items
        for col_name in ['impact_score', 'effort_score']:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='roadmap_items' AND column_name=%s
            """, (col_name,))
            
            if not cursor.fetchone():
                print(f"⚠️  Adicionando {col_name} em roadmap_items...")
                cursor.execute(f"""
                    ALTER TABLE roadmap_items ADD COLUMN {col_name} INTEGER DEFAULT 3
                """)
                print(f"✅ {col_name} adicionado")
            else:
                print(f"✅ {col_name} já existe")

        conn.commit()
        cursor.close()
        conn.close()
        
        print("="*60)
        print("✅ ESQUEMA DO RENDER CORRIGIDO COM SUCESSO!")
        print("="*60 + "\n")
        return True

    except psycopg2.errors.DuplicateColumn as e:
        print(f"⚠️  Coluna duplicada (já existe): {str(e)}")
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return False

if __name__ == "__main__":
    fix_render()
