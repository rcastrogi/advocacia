#!/usr/bin/env python
"""Script para analisar planos e features."""
import sys
import os
os.chdir(r'f:\PROJETOS\advocacia\advocacia_saas')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import BillingPlan, Feature, plan_features

app = create_app()

with app.app_context():
    print("=" * 80)
    print("ANALISE DOS PLANOS E FEATURES")
    print("=" * 80)
    
    # Listar todas as features disponiveis
    features = Feature.query.filter_by(is_active=True).order_by(Feature.module, Feature.display_order).all()
    
    print("\n>>> FEATURES DISPONIVEIS:")
    print("-" * 80)
    for f in features:
        print(f"  [{f.slug}] {f.name} (tipo: {f.feature_type}, modulo: {f.module})")
    
    print("\n" + "=" * 80)
    print(">>> PLANOS E SUAS FEATURES:")
    print("=" * 80)
    
    plans = BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    
    for plan in plans:
        multi_users = plan.get_feature_limit('multi_users') or 1
        plan_type = "ESCRITORIO" if multi_users > 1 else "INDIVIDUAL"
        
        print(f"\n[{plan_type}] {plan.name} - R${plan.monthly_fee:.2f}")
        print(f"  Slug: {plan.slug}")
        print(f"  Descricao: {plan.description}")
        print(f"  Tipo: {plan.plan_type}")
        print(f"  Multi-usuarios: {multi_users}")
        print(f"  Features:")
        
        # Buscar features do plano usando a tabela de associacao
        from sqlalchemy import select
        stmt = select(plan_features.c.feature_id, plan_features.c.limit_value).where(
            plan_features.c.plan_id == plan.id
        )
        results = db.session.execute(stmt).fetchall()
        for feature_id, limit_value in results:
            feature = Feature.query.get(feature_id)
            if feature:
                print(f"    - {feature.slug}: {limit_value}")
