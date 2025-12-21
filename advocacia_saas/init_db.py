"""
Script para inicializar o banco de dados da aplicação
"""

from app import create_app, db, migrate
from app.models import User
from flask_migrate import upgrade


def init_db():
    """Inicializa o banco de dados e cria usuário administrador padrão"""
    app = create_app()

    with app.app_context():
        # Aplicar migrações pendentes
        upgrade()
        print("Migrações do banco de dados aplicadas com sucesso!")

        # Verificar se já existe um usuário master
        master_user = User.query.filter_by(user_type="master").first()

        if not master_user:
            # Criar usuário master padrão
            admin = User(
                username="admin",
                email="admin@advocaciasaas.com",
                full_name="Administrador do Sistema",
                user_type="master",
            )
            admin.set_password("admin123")

            db.session.add(admin)
            db.session.commit()

            print("Usuário administrador criado!")
            print("Email: admin@advocaciasaas.com")
            print("Senha: admin123")
            print("IMPORTANTE: Altere a senha padrão após o primeiro login!")
        else:
            print("Usuário master já existe no sistema.")


if __name__ == "__main__":
    init_db()
