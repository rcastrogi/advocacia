#!/bin/bash
echo "🔧 Executando scripts de exemplo no Render..."

# Ativar ambiente virtual se existir
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Executar scripts de exemplo
python create_real_case_examples.py
python create_real_case_templates.py

echo "✅ Scripts executados!"