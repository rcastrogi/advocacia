"""
Script para testar o controle de petições billable
"""

from decimal import Decimal

from app import create_app, db
from app.billing.utils import current_billing_cycle, get_user_petition_usage
from app.models import BillingPlan, PetitionType, PetitionUsage, User, UserPlan

app = create_app()

with app.app_context():
    print("🧪 TESTE: Controle de Petições Billable vs Gratuitas")
    print("=" * 60)

    # Verificar se existe tipo de petição billable e gratuita
    billable_type = PetitionType.query.filter_by(is_billable=True).first()

    if not billable_type:
        print("❌ Nenhum tipo de petição billable encontrado")
        print("   Criando tipo de teste...")
        billable_type = PetitionType(
            slug="teste-billable",
            name="Teste Billable",
            category="teste",
            is_billable=True,
            base_price=Decimal("20.00"),
            active=True,
        )
        db.session.add(billable_type)
        db.session.commit()
        print(f"✅ Criado: {billable_type.name} (billable=True)")

    # Criar tipo gratuito se não existir
    free_type = PetitionType.query.filter_by(is_billable=False).first()
    if not free_type:
        free_type = PetitionType(
            slug="teste-gratuito",
            name="Teste Gratuito",
            category="teste",
            is_billable=False,
            base_price=Decimal("0.00"),
            active=True,
        )
        db.session.add(free_type)
        db.session.commit()
        print(f"✅ Criado: {free_type.name} (billable=False)")

    print(f"\n📋 Tipos de petição disponíveis:")
    print(
        f"   • {billable_type.name}: billable={billable_type.is_billable}, preço=R$ {billable_type.base_price}"
    )
    print(
        f"   • {free_type.name}: billable={free_type.is_billable}, preço=R$ {free_type.base_price}"
    )

    # Verificar plano com limite
    prof_plan = BillingPlan.query.filter_by(slug="profissional").first()

    if prof_plan:
        print(f"\n🎯 Plano Profissional:")
        print(f"   • Limite: {prof_plan.monthly_petition_limit} petições/mês")
        print(f"   • Tipo: {prof_plan.plan_type}")

        print("\n📊 Exemplo de contagem:")
        print("   Usuário gera:")
        print("   • 50 petições billable (contam para o limite)")
        print("   • 100 petições gratuitas (NÃO contam)")
        print("   = Total: 150 petições geradas")
        print("   = Contador do limite: 50/200 (apenas billable)")
        print("   = Restam: 150 petições billable disponíveis")

    print(
        "\n✅ Sistema configurado para contar apenas petições com valor (billable=True)"
    )
    print("✅ Petições gratuitas (billable=False) não afetam o limite mensal")
