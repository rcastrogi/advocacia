from app import create_app, db
from app.models import Client, Dependent, User

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {"db": db, "User": User, "Client": Client, "Dependent": Dependent}


if __name__ == "__main__":
    with app.app_context():
        # Corrigir schema do banco antes de iniciar
        try:
            from init_db_schema import init_schema_fixes
            init_schema_fixes()
        except Exception as e:
            print(f"⚠️  Erro ao executar init_db_schema: {str(e)}")
        
        # Só cria tabelas se for desenvolvimento local com SQLite
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            db.create_all()

            # Create a default master user if no users exist
            if User.query.count() == 0:
                admin = User(
                    username="admin",
                    email="admin@petitio.com",
                    full_name="Administrador",
                    user_type="master",
                )
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()
                print("Usuario master criado: admin@petitio.com / admin123")

    app.run(debug=True, host="127.0.0.1", port=5000)
