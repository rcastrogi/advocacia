#!/usr/bin/env python3
"""
Script para testar o novo sistema de preços flexíveis
"""

from app import create_app
from app.models import BillingPlan


def test_pricing():
    app = create_app()
    with app.app_context():
        # Buscar um plano para testar
        plan = BillingPlan.query.filter_by(slug="profissional").first()
        if not plan:
            print("Plano não encontrado")
            return

        print(f"Plano: {plan.name}")
        print(f"Taxa mensal: R$ {plan.monthly_fee}")
        print(f"Desconto: {plan.discount_percentage}%")
        print(f"Períodos suportados: {plan.supported_periods}")
        print()

        # Testar cálculos de preço
        for period in plan.supported_periods:
            price = plan.get_price_for_period(period)
            label = plan.get_period_label(period)
            print(f"{label}: R$ {price:.2f}")


if __name__ == "__main__":
    test_pricing()
