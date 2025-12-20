"""
Script para adicionar coluna monthly_petition_limit à tabela billing_plans
"""

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Adicionar coluna ao banco
    with db.engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE billing_plans ADD COLUMN IF NOT EXISTS monthly_petition_limit INTEGER DEFAULT NULL"
            )
        )
        conn.commit()
        print("✅ Coluna monthly_petition_limit adicionada à tabela billing_plans")

    # Atualizar os planos com os limites
    from app.models import BillingPlan

    prof = BillingPlan.query.filter_by(slug="profissional").first()
    if prof:
        prof.monthly_petition_limit = 200
        print(f"✅ {prof.name}: limite de 200 petições/mês")

    escrit = BillingPlan.query.filter_by(slug="escritorio").first()
    if escrit:
        escrit.monthly_petition_limit = None  # ilimitado
        print(f"✅ {escrit.name}: petições ilimitadas")

    essencial = BillingPlan.query.filter_by(slug="essencial").first()
    if essencial:
        essencial.monthly_petition_limit = None  # ilimitado (mas paga por uso)
        print(f"✅ {essencial.name}: sem limite mensal (paga por uso)")

    db.session.commit()

    print("\n📋 Configuração final:")
    plans = (
        BillingPlan.query.filter_by(active=True).order_by(BillingPlan.monthly_fee).all()
    )
    for plan in plans:
        limit = (
            "ilimitadas"
            if plan.monthly_petition_limit is None
            else f"{plan.monthly_petition_limit} petições/mês"
        )
        print(f"  {plan.name}: {limit}")
