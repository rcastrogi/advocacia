#!/bin/bash
echo "🚀 Iniciando Petitio..."

# Executar migrações do banco
echo "📦 Aplicando migrações do banco..."
flask db upgrade || echo "⚠️  Migração não necessária ou já aplicada"

# Inicializar banco
python init_db.py
echo "✅ Banco inicializado"

# Executar scripts de exemplo (FORÇANDO EXECUÇÃO PARA RENDER)
python -c "
from app import create_app, db
from app.models import PetitionType
app = create_app()
with app.app_context():
    try:
        count = PetitionType.query.count()
        print(f'📊 Tipos de petição existentes: {count}')
        print('📝 Criando exemplos do sistema...')
        exec(open('create_real_case_examples.py').read())
        exec(open('create_real_case_templates.py').read())
        new_count = PetitionType.query.count()
        print(f'✅ Exemplos criados! Total: {new_count} tipos')
    except Exception as e:
        print(f'❌ Erro ao criar exemplos: {e}')
        import traceback
        traceback.print_exc()
"

exec "$@"