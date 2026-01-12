"""
Script para criar tabelas do Sistema de Notificações Inteligentes
Execute: python scripts/create_notification_tables.py
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

# URL do banco Render
DATABASE_URL = "postgresql://petitio_db_user:krGWlyjOxEJKLwgoNHBZjOzaMV1T0JZf@dpg-d54kpj6r433s73d37900-a.oregon-postgres.render.com/petitio_db"

def create_tables():
    engine = create_engine(DATABASE_URL)

    sql_preferences = """
    CREATE TABLE IF NOT EXISTS notification_preferences (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id) ON DELETE CASCADE,
        
        -- Canais
        email_enabled BOOLEAN DEFAULT TRUE,
        push_enabled BOOLEAN DEFAULT TRUE,
        in_app_enabled BOOLEAN DEFAULT TRUE,
        
        -- Tipos - Prazos
        deadline_email BOOLEAN DEFAULT TRUE,
        deadline_push BOOLEAN DEFAULT TRUE,
        deadline_in_app BOOLEAN DEFAULT TRUE,
        
        -- Tipos - Movimentações
        movement_email BOOLEAN DEFAULT TRUE,
        movement_push BOOLEAN DEFAULT FALSE,
        movement_in_app BOOLEAN DEFAULT TRUE,
        
        -- Tipos - Pagamentos
        payment_email BOOLEAN DEFAULT TRUE,
        payment_push BOOLEAN DEFAULT TRUE,
        payment_in_app BOOLEAN DEFAULT TRUE,
        
        -- Tipos - Petições/IA
        petition_email BOOLEAN DEFAULT TRUE,
        petition_push BOOLEAN DEFAULT FALSE,
        petition_in_app BOOLEAN DEFAULT TRUE,
        
        -- Tipos - Sistema
        system_email BOOLEAN DEFAULT TRUE,
        system_push BOOLEAN DEFAULT FALSE,
        system_in_app BOOLEAN DEFAULT TRUE,
        
        -- Horário de Silêncio
        quiet_hours_enabled BOOLEAN DEFAULT FALSE,
        quiet_hours_start TIME,
        quiet_hours_end TIME,
        quiet_hours_weekends BOOLEAN DEFAULT TRUE,
        
        -- Digest
        digest_enabled BOOLEAN DEFAULT FALSE,
        digest_frequency VARCHAR(20) DEFAULT 'daily',
        digest_time TIME,
        last_digest_sent TIMESTAMP,
        
        -- Prioridade
        min_priority_email INTEGER DEFAULT 1,
        min_priority_push INTEGER DEFAULT 2,
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    sql_queue = """
    CREATE TABLE IF NOT EXISTS notification_queue (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
        notification_type VARCHAR(50) NOT NULL,
        channel VARCHAR(20) NOT NULL,
        priority INTEGER DEFAULT 2,
        title VARCHAR(200) NOT NULL,
        message TEXT NOT NULL,
        link VARCHAR(500),
        data TEXT,
        
        -- Status
        status VARCHAR(20) DEFAULT 'pending',
        retry_count INTEGER DEFAULT 0,
        error_message TEXT,
        
        -- Timestamps
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        scheduled_for TIMESTAMP,
        sent_at TIMESTAMP
    );
    """

    sql_indexes = """
    CREATE INDEX IF NOT EXISTS ix_notification_preferences_user_id ON notification_preferences(user_id);
    CREATE INDEX IF NOT EXISTS ix_notification_queue_user_id ON notification_queue(user_id);
    CREATE INDEX IF NOT EXISTS ix_notification_queue_status ON notification_queue(status);
    """

    with engine.connect() as conn:
        print("Criando tabela notification_preferences...")
        conn.execute(text(sql_preferences))
        
        print("Criando tabela notification_queue...")
        conn.execute(text(sql_queue))
        
        print("Criando índices...")
        for idx in sql_indexes.strip().split(";"):
            if idx.strip():
                conn.execute(text(idx))
        
        conn.commit()
        print("✅ Tabelas criadas com sucesso!")

    # Verificar
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('notification_preferences', 'notification_queue')
        """))
        tables = [row[0] for row in result]
        print(f"\n📋 Tabelas encontradas: {tables}")

if __name__ == "__main__":
    create_tables()
