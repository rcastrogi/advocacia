"""
Script para testar login do cliente
"""

from app import create_app, db
from app.models import Client, User
from werkzeug.security import check_password_hash

app = create_app()

with app.app_context():
    print("🔍 Verificando usuário cliente...")

    # Buscar usuário
    user = User.query.filter_by(email="cliente@teste.com").first()

    if not user:
        print("❌ Usuário não encontrado: cliente@teste.com")
        print("\n💡 Execute: python create_test_client.py")
        exit()

    print(f"✅ Usuário encontrado: {user.email}")
    print(f"   - Username: {user.username}")
    print(f"   - Nome: {user.full_name}")
    print(f"   - Tipo: {user.user_type}")
    print(f"   - Ativo: {user.is_active}")

    # Verificar cliente associado
    client = Client.query.filter_by(user_id=user.id).first()

    if not client:
        print("❌ Cliente não encontrado para este usuário")
        exit()

    print(f"✅ Cliente encontrado: {client.full_name}")
    print(f"   - ID: {client.id}")
    print(f"   - Email: {client.email}")

    # Testar senha
    test_password = "123456"
    password_ok = check_password_hash(user.password_hash, test_password)

    if password_ok:
        print(f"✅ Senha '{test_password}' está correta!")
    else:
        print(f"❌ Senha '{test_password}' está incorreta!")
        print(f"   - Hash armazenado: {user.password_hash[:50]}...")

        # Tentar recriar senha
        print("\n🔄 Redefinindo senha...")
        user.set_password("123456")
        db.session.commit()
        print("✅ Senha redefinida para: 123456")

    print("\n" + "=" * 50)
    print("Credenciais de teste:")
    print("📧 Email: cliente@teste.com")
    print("🔑 Senha: 123456")
    print("🔗 URL: http://localhost:5000/portal/login")
