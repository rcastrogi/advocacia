#!/usr/bin/env python
"""Script para reestruturar planos com precos e features coerentes."""
import sys
import os
os.chdir(r'f:\PROJETOS\advocacia\advocacia_saas')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import BillingPlan, Feature, plan_features

app = create_app()

# Nova estrutura de planos
PLANOS = {
    # === PLANOS INDIVIDUAIS ===
    "per_usage": {
        "name": "Pay per Use",
        "description": "Pague apenas pelo que usar - ideal para comecar",
        "plan_type": "per_usage",
        "monthly_fee": 0.00,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "deadlines_basic": 1,
            "processes_management": 10,
            "documents_storage": 100,
            "multi_users": 1,
        }
    },
    "individual_basico": {
        "name": "Individual Basico",
        "description": "Para advogados autonomos iniciando a digitalizacao",
        "plan_type": "subscription",
        "monthly_fee": 49.90,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "petitions_templates": 5,
            "ai_petitions": 10,
            "ai_credits_monthly": 10,
            "deadlines_basic": 1,
            "deadlines_notifications": 1,
            "processes_management": 50,
            "documents_storage": 500,
            "financial_basic": 1,
            "multi_users": 1,
        }
    },
    "individual_profissional": {
        "name": "Individual Profissional",
        "description": "Recursos completos para advogados autonomos estabelecidos",
        "plan_type": "subscription",
        "monthly_fee": 119.90,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "petitions_templates": 20,
            "petitions_export": 1,
            "ai_petitions": 50,
            "ai_credits_monthly": 50,
            "ai_suggestions": 1,
            "ai_analysis": 20,
            "deadlines_basic": 1,
            "deadlines_notifications": 1,
            "deadlines_calendar": 1,
            "processes_management": 200,
            "processes_timeline": 1,
            "documents_storage": 2000,
            "documents_ocr": 1,
            "portal_cliente": 1,
            "portal_chat": 1,
            "financial_basic": 1,
            "financial_invoices": 1,
            "multi_users": 1,
            "priority_support": 1,
        }
    },
    
    # === PLANOS ESCRITORIO ===
    "escritorio_starter": {
        "name": "Escritorio Starter",
        "description": "Para pequenos escritorios de 2 a 3 advogados",
        "plan_type": "subscription",
        "monthly_fee": 199.90,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "petitions_templates": 30,
            "petitions_export": 1,
            "ai_petitions": 80,
            "ai_credits_monthly": 80,
            "ai_suggestions": 1,
            "ai_analysis": 30,
            "deadlines_basic": 1,
            "deadlines_notifications": 1,
            "deadlines_calendar": 1,
            "processes_management": 300,
            "processes_timeline": 1,
            "processes_documents": 1,
            "documents_storage": 3000,
            "documents_ocr": 1,
            "portal_cliente": 1,
            "portal_chat": 1,
            "portal_documents": 1,
            "financial_basic": 1,
            "financial_invoices": 1,
            "financial_reports": 1,
            "multi_users": 3,
            "priority_support": 1,
        }
    },
    "escritorio_profissional": {
        "name": "Escritorio Profissional",
        "description": "Para escritorios em crescimento de 4 a 10 advogados",
        "plan_type": "subscription",
        "monthly_fee": 399.90,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "petitions_templates": 50,
            "petitions_export": 1,
            "ai_petitions": 150,
            "ai_credits_monthly": 150,
            "ai_suggestions": 1,
            "ai_analysis": 80,
            "deadlines_basic": 1,
            "deadlines_notifications": 1,
            "deadlines_calendar": 1,
            "processes_management": 1000,
            "processes_timeline": 1,
            "processes_documents": 1,
            "documents_storage": 10000,
            "documents_ocr": 1,
            "portal_cliente": 1,
            "portal_chat": 1,
            "portal_documents": 1,
            "client_calendar": 1,
            "financial_basic": 1,
            "financial_invoices": 1,
            "financial_reports": 1,
            "multi_users": 10,
            "audit_logs": 1,
            "priority_support": 1,
            "custom_reports": 1,
        }
    },
    "escritorio_enterprise": {
        "name": "Escritorio Enterprise",
        "description": "Solucao completa com recursos ilimitados para grandes escritorios",
        "plan_type": "subscription",
        "monthly_fee": 899.90,
        "features": {
            "clients_management": 1,
            "dashboard": 1,
            "basic_reports": 1,
            "petitions_basic": 1,
            "petitions_templates": 999,  # ilimitado
            "petitions_export": 1,
            "ai_petitions": 200,
            "ai_credits_monthly": 200,
            "ai_suggestions": 1,
            "ai_analysis": 200,
            "ai_document_analysis": 1,
            "deadlines_basic": 1,
            "deadlines_notifications": 1,
            "deadlines_calendar": 1,
            "processes_management": 99999,  # ilimitado
            "processes_timeline": 1,
            "processes_documents": 1,
            "documents_storage": 99999,  # ilimitado
            "documents_ocr": 1,
            "portal_cliente": 1,
            "portal_chat": 1,
            "portal_documents": 1,
            "client_calendar": 1,
            "financial_basic": 1,
            "financial_invoices": 1,
            "financial_reports": 1,
            "honorarios": 1,
            "custas": 1,
            "multi_users": 999,  # ilimitado
            "audit_logs": 1,
            "api_access": 1,
            "white_label": 1,
            "priority_support": 1,
            "custom_reports": 1,
        }
    },
}

with app.app_context():
    print("=" * 80)
    print("REESTRUTURANDO PLANOS")
    print("=" * 80)
    
    # Desativar planos antigos
    old_plans = BillingPlan.query.filter(
        BillingPlan.slug.in_([
            'plano_basico', 'plano_profissional', 
            'escritorio_pequeno', 'escritorio_medio', 'escritorio_grande'
        ])
    ).all()
    
    for plan in old_plans:
        plan.active = False
        print(f"  Desativado: {plan.name}")
    
    db.session.commit()
    
    # Criar/Atualizar novos planos
    print("\n>>> CRIANDO NOVOS PLANOS:")
    print("-" * 80)
    
    for slug, plan_data in PLANOS.items():
        features_config = plan_data.pop("features")
        
        existing = BillingPlan.query.filter_by(slug=slug).first()
        
        if existing:
            # Atualiza plano existente
            for key, value in plan_data.items():
                setattr(existing, key, value)
            existing.active = True
            plan = existing
            
            # Remover features antigas
            db.session.execute(
                plan_features.delete().where(plan_features.c.plan_id == existing.id)
            )
            db.session.flush()
            print(f"  Atualizado: {plan_data['name']}")
        else:
            # Cria novo plano
            plan = BillingPlan(slug=slug, **plan_data, active=True)
            db.session.add(plan)
            db.session.flush()
            print(f"  Criado: {plan_data['name']}")
        
        # Adicionar features ao plano
        for feature_slug, value in features_config.items():
            feature = Feature.query.filter_by(slug=feature_slug).first()
            if feature:
                if isinstance(value, bool):
                    limit_value = 1 if value else 0
                elif isinstance(value, int):
                    limit_value = value
                else:
                    limit_value = None
                db.session.execute(
                    plan_features.insert().values(
                        plan_id=plan.id,
                        feature_id=feature.id,
                        limit_value=limit_value
                    )
                )
            else:
                print(f"    [AVISO] Feature nao encontrada: {feature_slug}")
    
    db.session.commit()
    
    # Mostrar resultado final
    print("\n" + "=" * 80)
    print(">>> PLANOS ATIVOS APOS REESTRUTURACAO:")
    print("=" * 80)
    
    plans = BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    
    for plan in plans:
        multi_users = plan.get_feature_limit('multi_users') or 1
        ai_credits = plan.get_feature_limit('ai_credits_monthly') or 0
        plan_type = "ESCRITORIO" if multi_users > 1 else "INDIVIDUAL"
        
        users_label = "Ilimitados" if multi_users >= 999 else str(multi_users)
        
        print(f"\n[{plan_type}] {plan.name}")
        print(f"  Preco: R${plan.monthly_fee:.2f}/mes")
        print(f"  Usuarios: {users_label}")
        print(f"  Creditos IA: {ai_credits}/mes")
        print(f"  Descricao: {plan.description}")
