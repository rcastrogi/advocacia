"""
Script para inicializar usuário admin no banco de dados.
Este script deve ser executado no Render.com após o deploy.
"""

import argparse
import secrets
import sys
import traceback
from datetime import datetime

from app import create_app, db
from app.models import User


def init_admin(email: str, password: str | None, force: bool = False):
    """Cria ou recria usuário administrador.

    - If `force` is False and an admin exists, the script exits without changes.
    - If `force` is True the script will attempt to delete the existing admin
      and create a new one. If deletion fails (FK constraints), it will fallback
      to updating the existing record and resetting the password.

    Returns the password used (useful when it was auto-generated).
    """
    app = create_app()

    with app.app_context():
        try:
            print(
                f"[{datetime.utcnow().isoformat()}] 📦 Criando tabelas do banco de dados..."
            )
            db.create_all()
            print(f"[{datetime.utcnow().isoformat()}] ✅ Tabelas criadas!")

            print(
                f"[{datetime.utcnow().isoformat()}] 🔍 Verificando se admin existe ({email})..."
            )
            admin = User.query.filter_by(email=email).first()
            print(
                f"[{datetime.utcnow().isoformat()}] 🔍 Resultado da busca: {repr(admin)}"
            )

            # Decide senha
            if not password:
                # Generate a reasonably strong password when none provided
                password = secrets.token_urlsafe(12)

            if admin and not force:
                print(
                    f"[{datetime.utcnow().isoformat()}] ✅ Usuário admin já existe e --force não foi usado. Nenhuma ação tomada."
                )
                try:
                    print(f"   Email: {admin.email}")
                    print(f"   Username: {admin.username}")
                except Exception:
                    pass
                return None

            if admin and force:
                print(
                    f"[{datetime.utcnow().isoformat()}] ⚠️  --force ativo: removendo usuário admin existente..."
                )
                try:
                    db.session.delete(admin)
                    db.session.commit()
                    print(
                        f"[{datetime.utcnow().isoformat()}] ✅ Usuário antigo removido. Criando novo usuário admin..."
                    )
                    admin = None
                except Exception:
                    print(
                        f"[{datetime.utcnow().isoformat()}] ❗ Falha ao remover admin (possível restrição). Tentando atualizar o usuário existente..."
                    )
                    db.session.rollback()

            if not admin:
                admin = User(
                    username="admin",
                    email=email,
                    full_name="Administrador do Sistema",
                    user_type="master",
                    oab_number="123456",
                )
                # add then set password to ensure any hooks have an object
                db.session.add(admin)

            # Set password with skip_history_check when available
            try:
                admin.set_password(password, skip_history_check=True)
            except TypeError:
                try:
                    admin.set_password(password)
                except Exception:
                    print(
                        f"[{datetime.utcnow().isoformat()}] ❗ Erro ao definir a senha do admin:"
                    )
                    traceback.print_exc()
                    db.session.rollback()
                    raise

            db.session.commit()

            print(
                f"[{datetime.utcnow().isoformat()}] ✅ Usuário admin criado/atualizado com sucesso!"
            )
            print("\n" + "=" * 60)
            print("CREDENCIAIS DE LOGIN")
            print("=" * 60)
            print(f"📧 Email: {email}")
            print(f"🔑 Senha: {password}")
            print("=" * 60)
            print("\n⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
            print("📋 Política de senhas:")
            print("   • Senhas expiram após 90 dias")
            print("   • Não pode reutilizar as últimas 3 senhas")

            return password

        except Exception:
            print(f"[{datetime.utcnow().isoformat()}] ❗ Erro ao inicializar admin:")
            traceback.print_exc()
            sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="Inicializa ou recria usuário admin")
    p.add_argument("--email", default="admin@advocaciasaas.com", help="Email do admin")
    p.add_argument(
        "--password", default=None, help="Senha do admin (se omitida, será gerada)"
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Recria o admin: remove e cria novamente (ou redefine a senha)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    pw = init_admin(args.email, args.password, args.force)
    if pw is None:
        print("Nenhuma alteração feita.")
    else:
        print(f"Senha usada: {pw}")
