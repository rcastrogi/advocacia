"""
Migration: Adiciona campos de segurança de senha ao modelo User

Campos adicionados:
- password_changed_at: Data da última mudança de senha
- password_expires_at: Data de expiração da senha (3 meses após mudança)
- password_history: JSON com as últimas 3 senhas usadas
- force_password_change: Flag para forçar mudança de senha no próximo login
"""

from datetime import datetime, timedelta

from app import create_app, db
from app.models import User


def upgrade():
    """Adiciona os novos campos de segurança de senha"""
    app = create_app()

    with app.app_context():
        print("🔧 Aplicando migration: Campos de segurança de senha")

        # Verificar se as colunas já existem
        inspector = db.inspect(db.engine)
        columns = [col["name"] for col in inspector.get_columns("user")]

        needs_migration = False
        for col in [
            "password_changed_at",
            "password_expires_at",
            "password_history",
            "force_password_change",
        ]:
            if col not in columns:
                needs_migration = True
                break

        if not needs_migration:
            print("✅ Campos já existem! Nenhuma migração necessária.")
            return

        # Adicionar colunas com SQL direto
        with db.engine.connect() as conn:
            try:
                print("📝 Adicionando coluna password_changed_at...")
                conn.execute(
                    db.text("ALTER TABLE user ADD COLUMN password_changed_at DATETIME")
                )
                conn.commit()
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  Erro ao adicionar password_changed_at: {e}")

            try:
                print("📝 Adicionando coluna password_expires_at...")
                conn.execute(
                    db.text("ALTER TABLE user ADD COLUMN password_expires_at DATETIME")
                )
                conn.commit()
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  Erro ao adicionar password_expires_at: {e}")

            try:
                print("📝 Adicionando coluna password_history...")
                conn.execute(
                    db.text(
                        "ALTER TABLE user ADD COLUMN password_history TEXT DEFAULT '[]'"
                    )
                )
                conn.commit()
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  Erro ao adicionar password_history: {e}")

            try:
                print("📝 Adicionando coluna force_password_change...")
                conn.execute(
                    db.text(
                        "ALTER TABLE user ADD COLUMN force_password_change BOOLEAN DEFAULT 0"
                    )
                )
                conn.commit()
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    print(f"⚠️  Erro ao adicionar force_password_change: {e}")

        # Atualizar usuários existentes
        print("\n🔄 Atualizando usuários existentes...")
        users = User.query.all()

        for user in users:
            if not user.password_changed_at:
                user.password_changed_at = datetime.utcnow()

            if not user.password_expires_at:
                user.password_expires_at = datetime.utcnow() + timedelta(days=90)

            if not user.password_history:
                user.password_history = "[]"

            if user.force_password_change is None:
                user.force_password_change = False

        db.session.commit()

        print(f"✅ {len(users)} usuários atualizados com sucesso!")
        print("\n" + "=" * 60)
        print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("\n📋 Política de senhas implementada:")
        print("  • Senhas expiram após 90 dias (3 meses)")
        print("  • Não pode reutilizar as últimas 3 senhas")
        print("  • Avisos 7 dias antes da expiração")
        print("  • Mudança forçada após expiração")


def downgrade():
    """Remove os campos de segurança de senha (rollback)"""
    app = create_app()

    with app.app_context():
        print("⚠️  ATENÇÃO: Removendo campos de segurança de senha...")

        with db.engine.connect() as conn:
            try:
                conn.execute(
                    db.text("ALTER TABLE user DROP COLUMN password_changed_at")
                )
                conn.execute(
                    db.text("ALTER TABLE user DROP COLUMN password_expires_at")
                )
                conn.execute(db.text("ALTER TABLE user DROP COLUMN password_history"))
                conn.execute(
                    db.text("ALTER TABLE user DROP COLUMN force_password_change")
                )
                conn.commit()
                print("✅ Rollback concluído")
            except Exception as e:
                print(f"❌ Erro no rollback: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
