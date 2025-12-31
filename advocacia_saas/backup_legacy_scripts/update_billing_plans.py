#!/usr/bin/env python3
"""
Script para atualizar planos de cobrança com os novos campos de períodos flexíveis
"""

from app import create_app, db
from app.models import BillingPlan


def update_plans():
    app = create_app()
    with app.app_context():
        # Atualizar plano básico
        basic_plan = BillingPlan.query.filter_by(slug="basic").first()
        if basic_plan:
            basic_plan.supported_periods = ["1m", "3m", "6m", "1y", "2y", "3y"]
            basic_plan.discount_percentage = (
                10.0  # 10% de desconto para períodos maiores
            )

        # Atualizar plano profissional
        pro_plan = BillingPlan.query.filter_by(slug="professional").first()
        if pro_plan:
            pro_plan.supported_periods = ["1m", "3m", "6m", "1y", "2y", "3y"]
            pro_plan.discount_percentage = 15.0  # 15% de desconto

        # Atualizar plano enterprise
        enterprise_plan = BillingPlan.query.filter_by(slug="enterprise").first()
        if enterprise_plan:
            enterprise_plan.supported_periods = ["1m", "3m", "6m", "1y", "2y", "3y"]
            enterprise_plan.discount_percentage = 20.0  # 20% de desconto

        db.session.commit()
        print("Planos atualizados com sucesso!")


if __name__ == "__main__":
    update_plans()
