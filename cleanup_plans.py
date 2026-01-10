"""Script para limpar planos duplicados"""
import sys
import os
os.chdir(os.path.join(os.path.dirname(__file__), 'advocacia_saas'))
sys.path.insert(0, '.')

import logging
logging.disable(logging.CRITICAL)

from app import create_app, db
from app.models import BillingPlan

app = create_app()
with app.app_context():
    # Apagar planos antigos (IDs 1, 2, 3)
    planos_antigos = BillingPlan.query.filter(BillingPlan.id.in_([1, 2, 3])).all()
    for p in planos_antigos:
        print(f"Apagando: {p.name} (ID: {p.id})")
        db.session.delete(p)
    db.session.commit()
    
    print("\n=== PLANOS ATIVOS ===")
    for p in BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all():
        print(f"{p.name} - R${p.monthly_fee}")
