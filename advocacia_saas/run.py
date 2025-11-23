from app import create_app, db
from app.models import Client, Dependent, User

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "User": User, "Client": Client, "Dependent": Dependent}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create a default master user if no users exist
        if User.query.count() == 0:
            admin = User(
                username="admin",
                email="admin@advocaciasaas.com",
                full_name="Administrador",
                user_type="master",
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Usuário master criado: admin@advocaciasaas.com / admin123")

    app.run(debug=True, host="0.0.0.0", port=5000)
