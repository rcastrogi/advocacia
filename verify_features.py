#!/usr/bin/env python
"""Script para verificar status atual das features e planos."""
import sys
import os
os.chdir(r'f:\PROJETOS\advocacia\advocacia_saas')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import Feature, BillingPlan

app = create_app()

# Features que NAO devem aparecer nos planos
FEATURES_OCULTAS = ['documents_ocr', 'api_access', 'white_label', 'multi_users']

with app.app_context():
    print("=" * 80)
    print("VERIFICACAO DE FEATURES E PLANOS")
    print("=" * 80)
    
    # 1. Verificar features nao implementadas
    print("\n>>> STATUS DAS FEATURES NAO IMPLEMENTADAS:")
    print("-" * 80)
    for slug in FEATURES_OCULTAS:
        feature = Feature.query.filter_by(slug=slug).first()
        if feature:
            status = "INATIVA" if not feature.is_active else "ATIVA (deveria estar inativa!)"
            print(f"  {slug:25} - {feature.name:30} [{status}]")
        else:
            print(f"  {slug:25} - NAO EXISTE NO BANCO")
    
    # 2. Listar todas as features ativas que serao exibidas
    print("\n>>> FEATURES QUE SERAO EXIBIDAS NOS PLANOS:")
    print("-" * 80)
    features = Feature.query.filter_by(is_active=True).order_by(Feature.module, Feature.display_order).all()
    for f in features:
        if f.slug not in FEATURES_OCULTAS:
            print(f"  + {f.name} ({f.slug})")
    
    # 3. Mostrar planos ativos
    print("\n>>> PLANOS ATIVOS E SUAS FEATURES:")
    print("-" * 80)
    
    plans = BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    for plan in plans:
        # Verificar se e plano de escritorio
        multi_limit = plan.get_feature_limit('multi_users')
        is_office = multi_limit is not None and multi_limit > 1
        tipo = "[Escritorio]" if is_office else "[Individual]"
        
        print(f"\n  {plan.name} {tipo} - R${plan.monthly_fee:.2f}/mes")
        
        features_visiveis = []
        features_ocultas = []
        
        for feature in plan.features:
            if not feature.is_active or feature.slug in FEATURES_OCULTAS:
                features_ocultas.append(feature)
            else:
                features_visiveis.append(feature)
        
        print(f"     Features visiveis: {len(features_visiveis)}")
        for f in features_visiveis:
            limit = plan.get_feature_limit(f.slug)
            limit_str = f" [{limit}]" if limit and limit > 1 else ""
            print(f"       + {f.name}{limit_str}")
        
        if features_ocultas:
            print(f"     Features ocultas: {len(features_ocultas)}")
            for f in features_ocultas:
                print(f"       - {f.name} (oculta)")
    
    print("\n" + "=" * 80)
    print("VERIFICACAO CONCLUIDA!")
    print("=" * 80)
