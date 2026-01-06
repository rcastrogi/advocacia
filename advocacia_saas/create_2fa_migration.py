#!/usr/bin/env python
"""
Script para criar/atualizar as tabelas com os novos campos de 2FA
Executar com: python create_2fa_migration.py
"""

import os
import sys
from datetime import datetime, timezone

# Adicionar o diretório do app ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["FLASK_ENV"] = "development"

from advocacia_saas.app import create_app, db
from advocacia_saas.app.models import AuditLog, Notification, User


def create_migration():
    """Cria migração automática dos novos campos"""

    app = create_app()

    print("\n" + "█" * 70)
    print("█ MIGRAÇÃO DE SCHEMA PARA MELHORIAS DE 2FA")
    print("█" * 70)

    with app.app_context():
        print("\n📋 Verificando schema do banco de dados...")

        # Verificar se as colunas existem
        inspector = db.inspect(db.engine)
        user_columns = {col["name"] for col in inspector.get_columns("user")}

        columns_to_check = [
            "two_factor_failed_attempts",
            "two_factor_locked_until",
            "two_factor_enabled",
            "two_factor_method",
            "totp_secret",
            "two_factor_backup_codes",
            "two_factor_last_used",
            "email_2fa_code",
            "email_2fa_code_expires",
        ]

        print("\n📊 Status das colunas 2FA na tabela 'user':")
        missing_columns = []

        for col in columns_to_check:
            exists = col in user_columns
            status = "✓" if exists else "✗"
            print(f"  {status} {col}")
            if not exists:
                missing_columns.append(col)

        if missing_columns:
            print(f"\n⚠️  {len(missing_columns)} coluna(s) faltando!")
            print("\n🔧 Criando as colunas faltantes...")

            # Criar as colunas faltantes via SQL
            with db.engine.begin() as connection:
                for col_name in missing_columns:
                    try:
                        if col_name == "two_factor_failed_attempts":
                            connection.exec_driver_sql(
                                f'ALTER TABLE "user" ADD COLUMN {col_name} INTEGER DEFAULT 0'
                            )
                        elif col_name == "two_factor_locked_until":
                            connection.exec_driver_sql(
                                f'ALTER TABLE "user" ADD COLUMN {col_name} TIMESTAMP'
                            )
                        else:
                            connection.exec_driver_sql(
                                f'ALTER TABLE "user" ADD COLUMN {col_name} VARCHAR'
                            )
                        print(f"  ✓ Criada: {col_name}")
                    except Exception as e:
                        if "already exists" in str(e):
                            print(f"  ℹ️  Já existe: {col_name}")
                        else:
                            print(f"  ⚠️  Erro ao criar {col_name}: {e}")
        else:
            print("\n✅ Todas as colunas já existem!")

        # Verificar tabela de notificações
        print("\n📊 Verificando tabela de notificações...")
        try:
            notification_count = Notification.query.count()
            print(f"  ✓ Tabela 'notifications' existe ({notification_count} registros)")
        except Exception as e:
            print(f"  ✗ Erro ao acessar tabela: {e}")

        # Verificar tabela de auditoria
        print("\n📊 Verificando tabela de auditoria...")
        try:
            audit_count = AuditLog.query.count()
            print(f"  ✓ Tabela 'audit_log' existe ({audit_count} registros)")

            # Contar eventos de 2FA
            two_fa_events = AuditLog.query.filter(AuditLog.action.like("%2fa%")).count()
            print(f"  ✓ Eventos de 2FA auditados: {two_fa_events}")
        except Exception as e:
            print(f"  ✗ Erro ao acessar tabela: {e}")

        print("\n✅ Verificação de schema concluída!")

        # Estatísticas gerais
        print("\n📈 Estatísticas Gerais:")
        try:
            total_users = User.query.count()
            users_with_2fa = User.query.filter_by(two_factor_enabled=True).count()
            users_blocked = User.query.filter(
                User.two_factor_locked_until > datetime.now(timezone.utc)
            ).count()

            print(f"  - Total de usuários: {total_users}")
            print(f"  - Usuários com 2FA: {users_with_2fa}")
            print(f"  - Usuários bloqueados (rate limit): {users_blocked}")
        except Exception as e:
            print(f"  ✗ Erro ao gerar estatísticas: {e}")


if __name__ == "__main__":
    try:
        create_migration()
    except Exception as e:
        print(f"\n❌ ERRO: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
