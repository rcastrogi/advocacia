"""Adicionar feature de exportacao a todos os planos"""

import os
import sys

os.chdir(os.path.join(os.path.dirname(__file__), "advocacia_saas"))
sys.path.insert(0, ".")

import logging

logging.disable(logging.CRITICAL)

from app import create_app, db
from app.models import BillingPlan, Feature, plan_features

app = create_app()
with app.app_context():
    export_feature = Feature.query.filter_by(slug="petitions_export").first()

    # Adicionar a TODOS os planos ativos
    planos_ativos = BillingPlan.query.filter_by(active=True).all()
    for plano in planos_ativos:
        tem_export = (
            db.session.query(plan_features)
            .filter_by(plan_id=plano.id, feature_id=export_feature.id)
            .first()
        )
        if not tem_export:
            stmt = plan_features.insert().values(
                plan_id=plano.id, feature_id=export_feature.id, limit_value=1
            )
            db.session.execute(stmt)
            print(f"Adicionado petitions_export ao plano: {plano.name}")
        else:
            print(f"{plano.name} ja tem petitions_export")

    db.session.commit()
    print()
    print("=== VERIFICACAO FINAL ===")
    for plano in planos_ativos:
        tem = (
            db.session.query(plan_features)
            .filter_by(plan_id=plano.id, feature_id=export_feature.id)
            .first()
        )
        status = "OK" if tem else "FALTA"
        print(f"{plano.name}: {status}")
