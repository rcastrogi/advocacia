#!/usr/bin/env bash
# Script de build para Render.com

set -o errexit

echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Inicializando banco de dados ==="
python << 'PYEND'
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Criar todas as tabelas
    print("Criando tabelas...")
    db.create_all()
    print("OK - Tabelas criadas!")
    
    # Verificar e criar usuario admin
    print("Verificando usuario admin...")
    admin = User.query.filter_by(email="admin@advocaciasaas.com").first()
    
    if admin:
        print("OK - Usuario admin ja existe")
        print(f"   Email: {admin.email}")
    else:
        print("Criando usuario admin...")
        admin = User(
            username="admin",
            email="admin@advocaciasaas.com",
            full_name="Administrador do Sistema",
            user_type="master",
            oab_number="123456"
        )
        admin.set_password("admin123", skip_history_check=True)
        db.session.add(admin)
        db.session.commit()
        
        print("OK - Usuario admin criado!")
        print("")
        print("=" * 50)
        print("CREDENCIAIS DE LOGIN")
        print("=" * 50)
        print("Email: admin@advocaciasaas.com")
        print("Senha: admin123")
        print("=" * 50)
        print("IMPORTANTE: Altere a senha apos o primeiro login!")
PYEND

echo ""
echo "=== Build concluido com sucesso! ==="