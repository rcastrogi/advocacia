#!/bin/bash
echo "🚀 Iniciando Petitio..."
python init_db.py
echo "✅ Banco inicializado"
exec "$@"