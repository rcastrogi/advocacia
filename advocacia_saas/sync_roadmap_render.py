#!/usr/bin/env python3
"""
Script para sincronizar roadmap entre banco local e Render
e adicionar os campos impact_score/effort_score ao PostgreSQL do Render
"""

import os

import psycopg2
from app import create_app, db
from app.models import RoadmapItem
from psycopg2.extras import RealDictCursor

app = create_app()


def add_columns_to_render():
    """Adiciona colunas impact_score e effort_score ao PostgreSQL do Render"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("⚠️  DATABASE_URL não configurada. Pulando sincronização com Render.")
        return False

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("\n🔗 Conectado ao PostgreSQL do Render")

        # CORRIGIR: Adicionar votes_per_period em billing_plans se faltar
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='billing_plans' 
            AND column_name='votes_per_period'
        """)
        
        if not cursor.fetchone():
            print("⚠️  Coluna 'votes_per_period' faltando em billing_plans. Adicionando...")
            cursor.execute("""
                ALTER TABLE billing_plans 
                ADD COLUMN votes_per_period INTEGER DEFAULT 0
            """)
            print("✅ Coluna 'votes_per_period' adicionada ao Render")

        # Verificar se as colunas já existem
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='roadmap_items' 
            AND column_name IN ('impact_score', 'effort_score')
        """)

        existing_columns = [row[0] for row in cursor.fetchall()]

        if "impact_score" not in existing_columns:
            cursor.execute("""
                ALTER TABLE roadmap_items 
                ADD COLUMN impact_score INTEGER DEFAULT 3
            """)
            print("✅ Coluna 'impact_score' adicionada ao Render")
        else:
            print("⏭️  Coluna 'impact_score' já existe no Render")

        if "effort_score" not in existing_columns:
            cursor.execute("""
                ALTER TABLE roadmap_items 
                ADD COLUMN effort_score INTEGER DEFAULT 3
            """)
            print("✅ Coluna 'effort_score' adicionada ao Render")
        else:
            print("⏭️  Coluna 'effort_score' já existe no Render")

        conn.commit()
        cursor.close()
        conn.close()

        return True

    except psycopg2.errors.DuplicateColumn:
        print("⏭️  Colunas já existem no Render")
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar ao Render: {str(e)}")
        if conn:
            conn.rollback()
            cursor.close()
            conn.close()
        return False


def sync_roadmap_with_render():
    """Sincroniza items do banco local para o Render"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("⚠️  DATABASE_URL não configurada.")
        return False

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("\n📤 Sincronizando com Render...\n")

        # Buscar todos os items locais
        with app.app_context():
            local_items = RoadmapItem.query.all()
            print(f"   Total de itens locais: {len(local_items)}")

        synced = 0
        for item in local_items:
            try:
                # Verificar se item existe no Render
                cursor.execute(
                    "SELECT id FROM roadmap_items WHERE slug = %s", (item.slug,)
                )
                remote_item = cursor.fetchone()

                if remote_item:
                    # Atualizar campos de impacto/esforço
                    cursor.execute(
                        """
                        UPDATE roadmap_items 
                        SET impact_score = %s, 
                            effort_score = %s,
                            priority = %s,
                            status = %s,
                            description = %s,
                            detailed_description = %s,
                            business_value = %s,
                            estimated_effort = %s
                        WHERE slug = %s
                    """,
                        (
                            item.impact_score,
                            item.effort_score,
                            item.priority,
                            item.status,
                            item.description,
                            item.detailed_description,
                            item.business_value,
                            item.estimated_effort,
                            item.slug,
                        ),
                    )
                    synced += 1

            except Exception as e:
                print(f"   ❌ Erro ao sincronizar {item.slug}: {str(e)}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✅ {synced} itens sincronizados com Render\n")
        return True

    except Exception as e:
        print(f"❌ Erro ao sincronizar com Render: {str(e)}")
        return False


def verify_sync():
    """Verifica quantos items foram sincronizados"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return False

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Contar items no Render
        cursor.execute(
            "SELECT COUNT(*) FROM roadmap_items WHERE impact_score IS NOT NULL"
        )
        render_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        with app.app_context():
            local_count = RoadmapItem.query.filter(
                RoadmapItem.impact_score != None
            ).count()

        print(f"\n✅ VERIFICAÇÃO DE SINCRONIZAÇÃO:")
        print(f"   Local:  {local_count} itens com impact_score")
        print(f"   Render: {render_count} itens com impact_score")

        if local_count == render_count:
            print(f"   🎉 SINCRONIZADO!\n")
            return True
        else:
            print(f"   ⚠️  Diferença detectada\n")
            return False

    except Exception as e:
        print(f"❌ Erro ao verificar sincronização: {str(e)}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔄 SINCRONIZANDO ROADMAP COM RENDER")
    print("=" * 80)

    # Step 1: Adicionar colunas ao Render
    if add_columns_to_render():
        # Step 2: Sincronizar dados
        if sync_roadmap_with_render():
            # Step 3: Verificar sincronização
            verify_sync()
    else:
        print("\n⚠️  Executando apenas com banco local")
        with app.app_context():
            items = RoadmapItem.query.all()
            print(f"\n✅ Banco local: {len(items)} itens no roadmap\n")
