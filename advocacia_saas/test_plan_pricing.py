#!/usr/bin/env python3
"""Teste do sistema de planos com múltiplos períodos"""

from app import create_app
from app.models import BillingPlan

def test_plan_pricing():
    """Testa o cálculo de preços para diferentes períodos"""
    app = create_app()
    app.app_context().push()

    # Simular plano para teste de cálculo
    class MockPlan:
        def __init__(self, name, plan_type, monthly_fee, supported_periods, period_discounts):
            self.name = name
            self.plan_type = plan_type
            self.monthly_fee = monthly_fee
            self.supported_periods = supported_periods
            self.period_discounts = period_discounts

        def get_price_for_period(self, period):
            """Calcula o preço para um período específico com desconto específico do período"""
            if period not in self.supported_periods:
                return None

            # Converter período para meses
            period_months = self._period_to_months(period)
            base_price = float(self.monthly_fee) * period_months

            # Aplicar desconto específico do período
            discounts = self.period_discounts or {}
            discount_percentage = discounts.get(period, 0.0)
            discount_amount = base_price * (discount_percentage / 100.0)

            return round(base_price - discount_amount, 2)

        def _period_to_months(self, period):
            """Converte período para meses"""
            period_map = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "2y": 24, "3y": 36}
            return period_map.get(period, 1)

    plan = MockPlan(
        name="Plano Profissional",
        plan_type="monthly",
        monthly_fee=99.90,
        supported_periods=['1m', '3m', '6m', '1y', '2y'],
        period_discounts={'1m': 0.0, '3m': 5.0, '6m': 7.0, '1y': 9.0, '2y': 13.0, '3y': 20.0}
    )

    print("🧪 TESTE DO SISTEMA DE PREÇOS")
    print("=" * 50)
    print(f"Plano: {plan.name}")
    print(f"Tipo: {plan.plan_type}")
    print(f"Preço mensal base: R$ {plan.monthly_fee}")
    print(f"Períodos suportados: {plan.supported_periods}")
    print("Descontos por período:")
    for period, discount in plan.period_discounts.items():
        if period in plan.supported_periods:
            print(f"  {period}: {discount}%")
    print()

    print("📊 PREÇOS CALCULADOS POR PERÍODO:")
    print("-" * 40)

    for period in ['1m', '3m', '6m', '1y', '2y', '3y']:
        if period in plan.supported_periods:
            price = plan.get_price_for_period(period)
            print(f"  {period}: R$ {price}")
        else:
            print(f"  {period}: NÃO SUPORTADO")
    print()
    print("✅ Teste concluído!")

if __name__ == "__main__":
    test_plan_pricing()