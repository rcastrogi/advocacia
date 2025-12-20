"""
Script para criar um cliente de teste com usuário para acesso ao portal
"""

from app import create_app, db
from app.models import Client, User

app = create_app()

with app.app_context():
    # Verificar se já existe
    existing = User.query.filter_by(email="cliente@teste.com").first()
    if existing:
        print("❌ Cliente já existe: cliente@teste.com")
        exit()

    # Criar usuário para o cliente
    user = User(
        username="cliente_teste",
        email="cliente@teste.com",
        full_name="Cliente Teste",
        user_type="cliente",
        is_active=True,
    )
    user.set_password("123456")
    db.session.add(user)
    db.session.flush()

    # Pegar o advogado admin
    admin = User.query.filter_by(email="admin@advocaciasaas.com").first()

    # Criar cliente associado ao usuário
    client = Client(
        lawyer_id=admin.id,
        user_id=user.id,
        full_name="Cliente Teste",
        cpf_cnpj="12345678900",
        email="cliente@teste.com",
        mobile_phone="11999999999",
    )
    db.session.add(client)
    db.session.commit()

    print("✅ Cliente criado com sucesso!")
    print("\n📧 Email: cliente@teste.com")
    print("🔑 Senha: 123456")
    print("\n🔗 Acesse: http://localhost:5000/portal/login")
