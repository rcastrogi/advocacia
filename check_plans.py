#!/usr/bin/env python
"""Script para verificar planos no banco de dados."""

import sys

sys.path.insert(0, "advocacia_saas")

from app import create_app
from app.models import BillingPlan, PlanFeature

app = create_app()
with app.app_context():
    plans = (
        BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    )

    print(f"\n{'=' * 60}")
    print(f"TOTAL DE PLANOS ATIVOS: {len(plans)}")
    print(f"{'=' * 60}\n")

    for p in plans:
        # Get multi_users feature
        multi_users_feature = (
            PlanFeature.query.filter_by(plan_id=p.id)
            .join(PlanFeature.feature)
            .filter_by(slug="multi_users")
            .first()
        )

        multi_users = multi_users_feature.limit_value if multi_users_feature else 1

        plan_type = "ESCRITÓRIO" if multi_users > 1 else "INDIVIDUAL"

        print(f"[{plan_type}] {p.name}")
        print(f"  - ID: {p.id}")
        print(f"  - Preço: R${p.monthly_fee:.2f}")
        print(f"  - Slug: {p.slug}")
        print(f"  - Multi-usuários: {multi_users}")
        print()

    print(f"{'=' * 60}")
