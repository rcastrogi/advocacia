"""
Script para listar os planos existentes no banco
"""

from app import create_app, db
from app.models import BillingPlan

app = create_app()

with app.app_context():
    plans = BillingPlan.query.all()

    print(f"\n📋 Total de planos: {len(plans)}\n")

    for plan in plans:
        print(f"ID: {plan.id}")
        print(f"Nome: {plan.name}")
        print(f"Tipo: {plan.plan_type}")
        print(f"Ativo: {plan.active}")
        print(f"Mensal: R$ {plan.monthly_fee}")
        print(f"Por uso: R$ {plan.usage_rate}")
        print(f"Descrição: {plan.description}")
        print("-" * 50)
