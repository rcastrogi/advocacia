#!/usr/bin/env python3
"""
Migração para adicionar funcionalidades avançadas do sistema de processos.
Inclui: Calendário, Automação e Relatórios.
"""

import os
import sys
from datetime import datetime, timezone

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from sqlalchemy import text


def run_migration():
    """Executa a migração das novas funcionalidades."""

    print("🚀 Iniciando migração das funcionalidades avançadas...")

    app = create_app()

    with app.app_context():
        try:
            # Criar tabelas do calendário
            print("📅 Criando tabelas do calendário...")
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    title VARCHAR(300) NOT NULL,
                    description TEXT,
                    start_datetime TIMESTAMP NOT NULL,
                    end_datetime TIMESTAMP NOT NULL,
                    all_day BOOLEAN DEFAULT FALSE,
                    location VARCHAR(300),
                    virtual_link VARCHAR(500),
                    event_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) DEFAULT 'normal',
                    process_id INTEGER REFERENCES processes(id),
                    client_id INTEGER REFERENCES client(id),
                    status VARCHAR(20) DEFAULT 'scheduled',
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    reminder_minutes_before INTEGER DEFAULT 60,
                    is_recurring BOOLEAN DEFAULT FALSE,
                    recurrence_rule VARCHAR(200),
                    recurrence_end_date DATE,
                    participants TEXT,
                    attendees TEXT,
                    notes TEXT,
                    outcome TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            )

            # Criar índices para calendar_events
            db.session.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_calendar_events_user_id ON calendar_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_calendar_events_start_datetime ON calendar_events(start_datetime);
                CREATE INDEX IF NOT EXISTS idx_calendar_events_process_id ON calendar_events(process_id);
                CREATE INDEX IF NOT EXISTS idx_calendar_events_client_id ON calendar_events(client_id);
            """)
            )

            # Criar tabelas de automação
            print("🤖 Criando tabelas de automação...")
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS process_automations (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    trigger_type VARCHAR(50) NOT NULL,
                    trigger_condition JSON DEFAULT '{}',
                    action_type VARCHAR(50) NOT NULL,
                    action_config JSON DEFAULT '{}',
                    applies_to_all_processes BOOLEAN DEFAULT FALSE,
                    specific_processes TEXT,
                    process_types TEXT,
                    execution_count INTEGER DEFAULT 0,
                    last_executed_at TIMESTAMP,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            )

            # Criar índices para process_automations
            db.session.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_process_automations_user_id ON process_automations(user_id);
                CREATE INDEX IF NOT EXISTS idx_process_automations_active ON process_automations(is_active);
            """)
            )

            # Criar tabelas de relatórios
            print("📊 Criando tabelas de relatórios...")
            db.session.execute(
                text("""
                CREATE TABLE IF NOT EXISTS process_reports (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    report_type VARCHAR(50) NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    filters JSON DEFAULT '{}',
                    report_data JSON DEFAULT '{}',
                    total_processes INTEGER DEFAULT 0,
                    active_processes INTEGER DEFAULT 0,
                    completed_processes INTEGER DEFAULT 0,
                    total_costs DECIMAL(12,2) DEFAULT 0.00,
                    average_resolution_time INTEGER,
                    status VARCHAR(20) DEFAULT 'generating',
                    error_message TEXT,
                    file_path VARCHAR(500),
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            )

            # Criar índices para process_reports
            db.session.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_process_reports_user_id ON process_reports(user_id);
                CREATE INDEX IF NOT EXISTS idx_process_reports_type ON process_reports(report_type);
                CREATE INDEX IF NOT EXISTS idx_process_reports_status ON process_reports(status);
                CREATE INDEX IF NOT EXISTS idx_process_reports_created_at ON process_reports(created_at);
            """)
            )

            # Verificar se as tabelas foram criadas
            tables_created = db.session.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('calendar_events', 'process_automations', 'process_reports')
            """)
            ).fetchall()

            created_tables = [row[0] for row in tables_created]

            print("✅ Tabelas criadas com sucesso!")
            for table in ["calendar_events", "process_automations", "process_reports"]:
                if table in created_tables:
                    print(f"   - {table}")
                else:
                    print(f"   ⚠️  {table} (já existia)")

            # Inserir algumas automações padrão para usuários existentes
            print("🔧 Inserindo automações padrão...")

            # Verificar se já existem automações
            existing_automations = db.session.execute(
                text("""
                SELECT COUNT(*) FROM process_automations
            """)
            ).scalar()

            if existing_automations == 0:
                # Inserir automação de lembrete de prazos
                db.session.execute(
                    text("""
                    INSERT INTO process_automations (
                        user_id, name, description, is_active, trigger_type,
                        trigger_condition, action_type, action_config,
                        applies_to_all_processes, created_at
                    )
                    SELECT
                        u.id,
                        'Lembrete Automático de Prazos',
                        'Notifica automaticamente sobre prazos processuais próximos do vencimento',
                        TRUE,
                        'deadline',
                        '{"days_before": 7}',
                        'notification',
                        '{"title": "Prazo Próximo do Vencimento", "message": "Um prazo processual está próximo do vencimento."}',
                        TRUE,
                        CURRENT_TIMESTAMP
                    FROM "user" u
                    WHERE u.user_type IN ('advogado', 'master')
                    LIMIT 1
                """)
                )

                print("   ✅ Automação de lembrete de prazos criada")

            # Commit das mudanças
            db.session.commit()

            print("🎉 Migração concluída com sucesso!")
            print("\n📋 Resumo das funcionalidades adicionadas:")
            print("   • Sistema de Calendário Jurídico")
            print("   • Automação de Processos")
            print("   • Relatórios Avançados")
            print("   • Métricas e Analytics")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro durante a migração: {str(e)}")
            raise


if __name__ == "__main__":
    run_migration()
