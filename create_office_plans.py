#!/usr/bin/env python
"""Script para criar planos de escritorio."""
import sys
import os
os.chdir(r'f:\PROJETOS\advocacia\advocacia_saas')
sys.path.insert(0, os.getcwd())

from app import create_app, db
from app.models import BillingPlan, Feature, plan_features

app = create_app()

OFFICE_PLANS = [
    {
        "slug": "escritorio_pequeno",
        "name": "Escritorio Pequeno",
        "description": "Ideal para escritorios de ate 3 advogados",
        "plan_type": "subscription",
        "monthly_fee": 149.00,
        "features": {
            "clients_management": True,
            "dashboard": True,
            "basic_reports": True,
            "petitions_basic": True,
            "petitions_templates": 10,
            "ai_petitions": 30,
            "deadlines_basic": True,
            "deadlines_notifications": True,
            "processes_management": 150,
            "documents_storage": 1000,
            "financial_basic": True,
            "multi_users": 3,
        }
    },
    {
        "slug": "escritorio_medio",
        "name": "Escritorio Profissional",
        "description": "Para escritorios em crescimento com ate 10 advogados",
        "plan_type": "subscription",
        "monthly_fee": 349.00,
        "features": {
            "clients_management": True,
            "dashboard": True,
            "basic_reports": True,
            "petitions_basic": True,
            "petitions_templates": 30,
            "petitions_export": True,
            "ai_petitions": 100,
            "ai_suggestions": True,
            "ai_analysis": 30,
            "deadlines_basic": True,
            "deadlines_notifications": True,
            "deadlines_calendar": True,
            "processes_management": 500,
            "processes_timeline": True,
            "processes_documents": True,
            "documents_storage": 5000,
            "documents_ocr": True,
            "portal_cliente": True,
            "portal_chat": True,
            "portal_documents": True,
            "financial_basic": True,
            "financial_invoices": True,
            "financial_reports": True,
            "multi_users": 10,
            "priority_support": True,
        }
    },
    {
        "slug": "escritorio_grande",
        "name": "Escritorio Enterprise",
        "description": "Solucao completa para grandes escritorios - ate 30 advogados",
        "plan_type": "subscription",
        "monthly_fee": 699.00,
        "features": {
            "clients_management": True,
            "dashboard": True,
            "basic_reports": True,
            "petitions_basic": True,
            "petitions_templates": 100,
            "petitions_export": True,
            "ai_petitions": 500,
            "ai_suggestions": True,
            "ai_analysis": 100,
            "deadlines_basic": True,
            "deadlines_notifications": True,
            "deadlines_calendar": True,
            "processes_management": 2000,
            "processes_timeline": True,
            "processes_documents": True,
            "documents_storage": 20000,
            "documents_ocr": True,
            "portal_cliente": True,
            "portal_chat": True,
            "portal_documents": True,
            "financial_basic": True,
            "financial_invoices": True,
            "financial_reports": True,
            "multi_users": 30,
            "api_access": True,
            "white_label": True,
            "priority_support": True,
        }
    },
]

with app.app_context():
    created = 0
    updated = 0
    skipped = 0
    
    print("Inicializando planos de escritorio...")
    print("-" * 50)
    
    for plan_data in OFFICE_PLANS:
        features_config = plan_data.pop("features")
        
        existing = BillingPlan.query.filter_by(slug=plan_data["slug"]).first()
        
        if existing:
            skipped += 1
            print(f"   Ja existe: {plan_data['name']}")
        else:
            # Cria novo plano
            plan = BillingPlan(**plan_data, active=True)
            db.session.add(plan)
            db.session.flush()  # Para obter o ID
            
            # Adicionar features ao plano
            for feature_slug, value in features_config.items():
                feature = Feature.query.filter_by(slug=feature_slug).first()
                if feature:
                    # Converter booleano para inteiro (1 = ativo)
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
            
            created += 1
            print(f"   Criado: {plan_data['name']}")
    
    db.session.commit()
    
    print("-" * 50)
    print(f"Resultado:")
    print(f"   Criados: {created}")
    print(f"   Atualizados: {updated}")
    print(f"   Ignorados: {skipped}")
    
    # Verificar todos os planos
    print("\n" + "=" * 50)
    print("TODOS OS PLANOS ATIVOS:")
    print("=" * 50)
    
    plans = BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    for p in plans:
        # Get multi_users feature
        from sqlalchemy import select
        stmt = select(plan_features.c.limit_value).where(
            plan_features.c.plan_id == p.id
        ).join(Feature, Feature.id == plan_features.c.feature_id).where(
            Feature.slug == 'multi_users'
        )
        result = db.session.execute(stmt).scalar()
        multi_users = result if result else 1
        
        plan_type = "ESCRITORIO" if multi_users > 1 else "INDIVIDUAL"
        print(f"[{plan_type}] {p.name} - R${p.monthly_fee:.2f} ({multi_users} usuarios)")
