#!/usr/bin/env python3
"""
Migração para adicionar campos de data efetiva de implementação e sistema de feedback ao roadmap
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from app import create_app, db
from app.models import RoadmapFeedback, RoadmapItem


def run_migration():
    """Executa a migração do banco de dados"""

    app = create_app()
    with app.app_context():
        print("🔄 Iniciando migração do roadmap...")

        try:
            # Verificar se as colunas já existem
            inspector = db.inspect(db.engine)

            # Verificar colunas da tabela roadmap_items
            roadmap_columns = [
                col["name"] for col in inspector.get_columns("roadmap_items")
            ]

            # Adicionar coluna implemented_at se não existir
            if "implemented_at" not in roadmap_columns:
                print(
                    "📝 Adicionando coluna 'implemented_at' à tabela roadmap_items..."
                )
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text(
                            "ALTER TABLE roadmap_items ADD COLUMN implemented_at TIMESTAMP"
                        )
                    )
                    conn.commit()
                print("✅ Coluna 'implemented_at' adicionada com sucesso!")
            else:
                print("ℹ️ Coluna 'implemented_at' já existe.")

            # Criar tabela roadmap_feedback se não existir
            if not inspector.has_table("roadmap_feedback"):
                print("📝 Criando tabela 'roadmap_feedback'...")

                # Criar tabela manualmente
                create_table_sql = """
                CREATE TABLE roadmap_feedback (
                    id INTEGER NOT NULL,
                    roadmap_item_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    rating_category VARCHAR(50),
                    title VARCHAR(200),
                    comment TEXT,
                    pros TEXT,
                    cons TEXT,
                    suggestions TEXT,
                    usage_frequency VARCHAR(20),
                    ease_of_use VARCHAR(20),
                    user_agent VARCHAR(500),
                    ip_address VARCHAR(45),
                    session_id VARCHAR(100),
                    is_anonymous BOOLEAN DEFAULT false,
                    is_featured BOOLEAN DEFAULT false,
                    status VARCHAR(20) DEFAULT 'pending',
                    admin_response TEXT,
                    responded_by INTEGER,
                    responded_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    FOREIGN KEY(roadmap_item_id) REFERENCES roadmap_items (id),
                    FOREIGN KEY(user_id) REFERENCES "user" (id),
                    FOREIGN KEY(responded_by) REFERENCES "user" (id)
                )
                """
                with db.engine.connect() as conn:
                    conn.execute(db.text(create_table_sql))
                    conn.commit()
                print("✅ Tabela 'roadmap_feedback' criada com sucesso!")
            else:
                print("ℹ️ Tabela 'roadmap_feedback' já existe.")

            # Verificar se há itens completados sem data de implementação
            completed_items = (
                RoadmapItem.query.filter_by(status="completed")
                .filter(RoadmapItem.implemented_at.is_(None))
                .all()
            )

            if completed_items:
                print(
                    f"📅 Atualizando {len(completed_items)} itens completados com data de implementação..."
                )

                for item in completed_items:
                    # Usar actual_completion_date se existir, senão usar uma data padrão
                    if item.actual_completion_date:
                        item.implemented_at = datetime.combine(
                            item.actual_completion_date, datetime.min.time()
                        )
                    else:
                        # Usar data de atualização ou criação como fallback
                        item.implemented_at = (
                            item.updated_at or item.created_at or datetime.utcnow()
                        )

                db.session.commit()
                print("✅ Datas de implementação atualizadas!")

            print("🎉 Migração concluída com sucesso!")

        except Exception as e:
            print(f"❌ Erro durante migração: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    run_migration()
