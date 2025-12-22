import sys

import psycopg2

# Configurações - ALTERE A SENHA DO SUPABASE AQUI
SUPABASE_URL = "postgresql://postgres:JjUujFkzJTLWx61E@db.wnagrszaulrlbmhzapye.supabase.co:5432/postgres"
RENDER_URL = "postgresql://petitio_db_user:krGWlyjOxEJKLwgoNHBZjOzaMV1T0JZf@dpg-d54kpj6r433s73d37900-a/petitio_db"


def migrate_data():
    try:
        # Conectar origem (Supabase)
        conn_origem = psycopg2.connect(SUPABASE_URL)
        cursor_origem = conn_origem.cursor()

        # Conectar destino (Render)
        conn_destino = psycopg2.connect(RENDER_URL)
        cursor_destino = conn_destino.cursor()

        # Tabelas para migrar (baseado no seu models.py)
        tables = [
            "user",
            "client",
            "dependent",
            "petition",
            "petition_template",
            "billing",
            "payment",
            "credit_package",
            "ai_credit",
            "chat_message",
            "document",
            "deadline",
            "quick_action",
            "notification",
            "testimonial",
        ]

        for table in tables:
            print(f"Migrando tabela: {table}")

            # Verificar se tabela existe na origem
            cursor_origem.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """,
                (table,),
            )

            if not cursor_origem.fetchone()[0]:
                print(f"Tabela {table} não existe na origem, pulando...")
                continue

            # Limpar tabela destino
            try:
                cursor_destino.execute(f"TRUNCATE TABLE {table} CASCADE")
            except:
                print(f"Não foi possível truncar {table}, pulando...")
                continue

            # Copiar dados
            cursor_origem.execute(f"SELECT * FROM {table}")
            rows = cursor_origem.fetchall()

            if rows:
                # Obter colunas
                cursor_origem.execute(
                    f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = %s ORDER BY ordinal_position
                """,
                    (table,),
                )
                columns = [col[0] for col in cursor_origem.fetchall()]

                # Inserir no destino
                placeholders = ",".join(["%s"] * len(columns))
                query = (
                    f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                )

                cursor_destino.executemany(query, rows)
                print(f"Migrados {len(rows)} registros da tabela {table}")

            conn_destino.commit()

        # Migrar sequences (IDs auto-increment)
        cursor_origem.execute("""
            SELECT sequence_name, last_value 
            FROM information_schema.sequences
        """)
        sequences = cursor_origem.fetchall()

        for seq_name, last_value in sequences:
            try:
                cursor_destino.execute(f"SELECT setval('{seq_name}', {last_value})")
                print(f"Sequence {seq_name} atualizada para {last_value}")
            except Exception as e:
                print(f"Erro na sequence {seq_name}: {e}")

        conn_destino.commit()

        print("✅ Migração concluída com sucesso!")

    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        if "conn_destino" in locals():
            conn_destino.rollback()
        sys.exit(1)

    finally:
        if "conn_origem" in locals():
            conn_origem.close()
        if "conn_destino" in locals():
            conn_destino.close()


if __name__ == "__main__":
    migrate_data()
