#!/usr/bin/env python
"""Script para desativar features que ainda não foram implementadas."""
import sys
import os
os.chdir(r'f:\PROJETOS\advocacia\advocacia_saas')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import Feature, BillingPlan, plan_features

app = create_app()

# Features que NÃO estão implementadas ainda
FEATURES_NAO_IMPLEMENTADAS = [
    'documents_ocr',       # OCR de documentos - não implementado
    'api_access',          # Acesso à API - não implementado
    'white_label',         # White Label - não implementado
    'multi_users',         # Não faz sentido mostrar para individuais (sempre 1)
]

# Features que devem aparecer apenas em planos de escritório
FEATURES_APENAS_ESCRITORIO = [
    'multi_users',         # Multi usuários só faz sentido em escritório
    'audit_logs',          # Logs de auditoria só em escritório
]

with app.app_context():
    print("=" * 80)
    print("LIMPANDO FEATURES NÃO IMPLEMENTADAS")
    print("=" * 80)
    
    # 1. Listar todas as features atuais
    print("\n>>> FEATURES CADASTRADAS:")
    print("-" * 80)
    features = Feature.query.order_by(Feature.module, Feature.display_order).all()
    for f in features:
        status = "✓ Ativa" if f.is_active else "✗ Inativa"
        print(f"  [{f.module:12}] {f.slug:30} - {f.name} ({status})")
    
    # 2. Desativar features não implementadas
    print("\n>>> DESATIVANDO FEATURES NÃO IMPLEMENTADAS:")
    print("-" * 80)
    for slug in FEATURES_NAO_IMPLEMENTADAS:
        feature = Feature.query.filter_by(slug=slug).first()
        if feature:
            feature.is_active = False
            print(f"  ✗ Desativada: {feature.name} ({slug})")
        else:
            print(f"  - Não encontrada: {slug}")
    
    db.session.commit()
    
    # 3. Verificar planos individuais e remover referência a multi_users
    print("\n>>> VERIFICANDO PLANOS INDIVIDUAIS:")
    print("-" * 80)
    
    individual_plans = BillingPlan.query.filter(
        BillingPlan.slug.in_(['per_usage', 'individual_basico', 'individual_profissional']),
        BillingPlan.active == True
    ).all()
    
    for plan in individual_plans:
        # Garantir que max_users é 1 para individuais
        if plan.max_users != 1:
            plan.max_users = 1
            print(f"  Ajustado max_users=1 para: {plan.name}")
        else:
            print(f"  ✓ {plan.name} já está com max_users=1")
    
    db.session.commit()
    
    # 4. Mostrar features ativas que serão exibidas
    print("\n>>> FEATURES ATIVAS (serão exibidas nos planos):")
    print("-" * 80)
    
    active_features = Feature.query.filter_by(is_active=True).order_by(Feature.display_order).all()
    for f in active_features:
        print(f"  ✓ {f.name} ({f.slug})")
    
    # 5. Mostrar resumo dos planos
    print("\n>>> RESUMO DOS PLANOS ATIVOS:")
    print("-" * 80)
    
    all_plans = BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    for plan in all_plans:
        active_features_count = len([f for f in plan.features if f.is_active])
        print(f"\n  📋 {plan.name} (R${plan.monthly_fee:.2f}/mês)")
        print(f"     Max usuários: {plan.max_users}")
        print(f"     Features ativas: {active_features_count}")
        
        # Listar features ativas do plano
        for feature in plan.features:
            if feature.is_active:
                limit = plan.get_feature_limit(feature.slug)
                limit_str = f" [{limit}]" if limit and limit > 1 else ""
                print(f"       - {feature.name}{limit_str}")
    
    print("\n" + "=" * 80)
    print("LIMPEZA CONCLUÍDA!")
    print("=" * 80)
