"""Script para criar tabela AICreditConfig diretamente no banco"""
from app import create_app, db
from app.models import AICreditConfig

app = create_app()
with app.app_context():
    # Criar tabela se não existir
    AICreditConfig.__table__.create(db.engine, checkfirst=True)
    print('Tabela ai_credit_configs criada!')
    
    # Popular com dados padrão
    AICreditConfig.seed_defaults()
    print('Dados padrão inseridos!')
    
    # Verificar
    configs = AICreditConfig.query.all()
    print(f'Total de configs: {len(configs)}')
    for c in configs:
        print(f'  - {c.operation_key}: {c.credit_cost} créditos (premium: {c.is_premium})')
