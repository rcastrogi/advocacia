"""
Script para inicializar usuário admin no banco de dados.
Este script deve ser executado no Render.com após o deploy.
"""

from app import create_app, db
from app.models import User


def init_admin():
    """Cria usuário administrador se não existir"""
    app = create_app()

    with app.app_context():
        # Verificar se já existe um usuário admin
        admin = User.query.filter_by(email="admin@advocaciasaas.com").first()

        if admin:
            print("✅ Usuário admin já existe!")
            print(f"   Email: {admin.email}")
            print(f"   Username: {admin.username}")
        else:
            print("🔧 Criando usuário administrador...")
            admin = User(
                username="admin",
                email="admin@advocaciasaas.com",
                full_name="Administrador do Sistema",
                user_type="master",
                oab_number="123456",
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

            print("✅ Usuário admin criado com sucesso!")
            print("\n" + "=" * 60)
            print("CREDENCIAIS DE LOGIN")
            print("=" * 60)
            print("📧 Email: admin@advocaciasaas.com")
            print("🔑 Senha: admin123")
            print("=" * 60)
            print("\n⚠️  IMPORTANTE: Altere a senha após o primeiro login!")


if __name__ == "__main__":
    init_admin()
