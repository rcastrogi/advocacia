#!/bin/bash
echo "🚀 Iniciando Petitio..."
python init_db.py
echo "✅ Banco inicializado"

# Executar scripts de exemplo (apenas se tabelas estiverem vazias)
python -c "
from app import create_app, db
from app.models import PetitionType
app = create_app()
with app.app_context():
    if PetitionType.query.count() == 0:
        print('📝 Criando exemplos do sistema...')
        exec(open('create_real_case_examples.py').read())
        exec(open('create_real_case_templates.py').read())
        print('✅ Exemplos criados!')
    else:
        print('ℹ️ Exemplos já existem, pulando criação...')
"

exec "$@"