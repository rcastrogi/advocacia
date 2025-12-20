"""
Script para cadastrar planos de exemplo no banco de dados
Execute: python seed_plans.py
"""

from decimal import Decimal

from app import create_app, db
from app.models import BillingPlan

app = create_app()

with app.app_context():
    # Verifica se já existem planos
    existing = BillingPlan.query.count()
    if existing > 0:
        print(f"❌ Já existem {existing} planos cadastrados.")
        print("   Se quiser recadastrar, delete os planos existentes primeiro.")
        exit(0)

    # Plano 1: Por Uso
    plan1 = BillingPlan(
        slug="essencial",
        name="Essencial",
        plan_type="per_usage",
        description="Pague apenas pelas petições que gerar. Ideal para escritórios pequenos.\n\nRecursos incluídos:\n• Petições ilimitadas\n• Clientes ilimitados\n• Templates básicos\n• Suporte por email\n• 1 usuário\n• 5GB armazenamento",
        monthly_fee=Decimal("0.00"),
        usage_rate=Decimal("15.00"),
        active=True,
    )

    # Plano 2: Mensal Básico
    plan2 = BillingPlan(
        slug="profissional",
        name="Profissional",
        plan_type="monthly",
        description="Petições ilimitadas com suporte prioritário. Ideal para escritórios em crescimento.\n\nRecursos incluídos:\n• Petições ilimitadas\n• Clientes ilimitados\n• Templates avançados\n• Suporte prioritário\n• 3 usuários\n• 20GB armazenamento",
        monthly_fee=Decimal("99.00"),
        usage_rate=Decimal("0.00"),
        active=True,
    )

    # Plano 3: Mensal Premium
    plan3 = BillingPlan(
        slug="escritorio",
        name="Escritório",
        plan_type="monthly",
        description="Solução completa para escritórios estabelecidos com múltiplos usuários.\n\nRecursos incluídos:\n• Petições ilimitadas\n• Clientes ilimitados\n• Templates premium\n• Suporte dedicado\n• 10 usuários\n• 100GB armazenamento\n• Acesso à API",
        monthly_fee=Decimal("199.00"),
        usage_rate=Decimal("0.00"),
        active=True,
    )

    db.session.add(plan1)
    db.session.add(plan2)
    db.session.add(plan3)
    db.session.commit()

    print("✅ 3 planos cadastrados com sucesso!")
    print("\n📋 Planos criados:")
    print(f"   1. {plan1.name} (ID: {plan1.id}) - R$ {plan1.usage_rate}/petição")
    print(f"   2. {plan2.name} (ID: {plan2.id}) - R$ {plan2.monthly_fee}/mês")
    print(f"   3. {plan3.name} (ID: {plan3.id}) - R$ {plan3.monthly_fee}/mês")
    print("\n🚀 Acesse http://localhost:5000 para ver os planos na página inicial!")
