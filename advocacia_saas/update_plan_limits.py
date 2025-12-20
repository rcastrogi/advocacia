from app import create_app, db
from app.models import BillingPlan

app = create_app()
with app.app_context():
    # Profissional: 200 petições/mês
    prof = BillingPlan.query.filter_by(slug="profissional").first()
    if prof:
        prof.monthly_petition_limit = 200
        print("✅ Profissional: limite de 200 petições/mês")

    # Escritório: ilimitado
    escrit = BillingPlan.query.filter_by(slug="escritorio").first()
    if escrit:
        escrit.monthly_petition_limit = None
        print("✅ Escritório: petições ilimitadas")

    # Essencial: ilimitado (paga por uso)
    essencial = BillingPlan.query.filter_by(slug="essencial").first()
    if essencial:
        essencial.monthly_petition_limit = None
        print("✅ Essencial: sem limite mensal (paga por uso)")

    db.session.commit()
    print("\n📋 Limites definidos com sucesso!")
