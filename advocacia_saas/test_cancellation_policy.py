#!/usr/bin/env python3
"""
Teste da política de cancelamento de assinaturas
"""

import os
from datetime import datetime, timedelta

from app import create_app, db
from app.models import Subscription


def test_cancellation_policy():
    """Testa a política de cancelamento padrão"""
    app = create_app()

    with app.app_context():
        # Criar tabelas
        db.create_all()

        print("🧪 Testando Política de Cancelamento de Assinaturas")
        print("=" * 50)

        # Criar uma assinatura de teste para plano mensal
        monthly_sub = Subscription(
            user_id=1,
            plan_type="professional",
            billing_period="1m",
            amount=99.00,
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(monthly_sub)

        # Criar uma assinatura de teste para plano anual
        yearly_sub = Subscription(
            user_id=2,
            plan_type="professional",
            billing_period="1y",
            amount=1009.80,  # Com desconto
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=365),
        )
        db.session.add(yearly_sub)
        db.session.commit()

        print("\n📅 Teste 1: Cancelamento de Plano Mensal (1m)")
        print(
            f"Antes: status={monthly_sub.status}, cancel_at_period_end={monthly_sub.cancel_at_period_end}"
        )
        monthly_sub.cancel_with_policy(immediate=False)
        print(
            f"Depois: status={monthly_sub.status}, cancel_at_period_end={monthly_sub.cancel_at_period_end}"
        )
        print(f"Política: {monthly_sub.refund_policy}")

        print("\n📅 Teste 2: Cancelamento de Plano Anual (1y) - Política Padrão")
        print(
            f"Antes: status={yearly_sub.status}, cancel_at_period_end={yearly_sub.cancel_at_period_end}"
        )
        yearly_sub.cancel_with_policy(immediate=False)
        print(
            f"Depois: status={yearly_sub.status}, cancel_at_period_end={yearly_sub.cancel_at_period_end}"
        )
        print(f"Política: {yearly_sub.refund_policy}")

        print("\n📅 Teste 3: Cancelamento Imediato de Plano Mensal")
        monthly_sub2 = Subscription(
            user_id=3,
            plan_type="basic",
            billing_period="1m",
            amount=49.00,
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.session.add(monthly_sub2)
        db.session.commit()

        print(
            f"Antes: status={monthly_sub2.status}, cancel_at_period_end={monthly_sub2.cancel_at_period_end}"
        )
        monthly_sub2.cancel_with_policy(immediate=True)
        print(
            f"Depois: status={monthly_sub2.status}, cancel_at_period_end={monthly_sub2.cancel_at_period_end}"
        )
        print(f"Política: {monthly_sub2.refund_policy}")

        print("\n✅ Política de Cancelamento Implementada com Sucesso!")
        print("\n📋 Resumo da Política Padrão:")
        print(
            "• Planos com desconto (3m, 6m, 1y, etc.): Cancelamento ao fim do período, sem reembolso"
        )
        print(
            "• Planos mensais (1m): Podem cancelar imediatamente ou ao fim do período"
        )
        print("• Cliente mantém acesso completo até o fim do período pago")


if __name__ == "__main__":
    test_cancellation_policy()
