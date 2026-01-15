#!/usr/bin/env bash
# Script de build para Render.com

set -o errexit -o pipefail

echo "=== Instalando dependencias ==="
pip install -r requirements.txt

echo ""
echo "=== Criando tabelas extras (se necessario) ==="
python -c "
from app import create_app, db
from app.models import AICreditConfig
app = create_app()
with app.app_context():
    try:
        AICreditConfig.__table__.create(db.engine, checkfirst=True)
        AICreditConfig.seed_defaults()
        print('AICreditConfig table OK')
    except Exception as e:
        print(f'AICreditConfig: {e}')
"

echo ""
echo "=== Inicializando banco de dados e criando admin (se necessario) ==="

# Configuracoes via env vars (opcionais)
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@advocaciasaas.com}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
# Quando ADMIN_FORCE for '1', 'true' ou 'yes' (case-insensitive), passamos --force
ADMIN_FORCE="${ADMIN_FORCE:-false}"

# Cria pasta de logs para inspecao post-deploy
mkdir -p build_logs
LOGFILE="build_logs/init_admin-$(date +%Y%m%d-%H%M%S).log"

echo "Executando init_admin.py (email=$ADMIN_EMAIL). Saida em: $LOGFILE"

# normalizar e verificar flag de force
ADMIN_FORCE_LC=$(echo "$ADMIN_FORCE" | tr '[:upper:]' '[:lower:]')
USE_FORCE=0
case "$ADMIN_FORCE_LC" in
  1|true|yes)
    USE_FORCE=1
    ;;
esac

if [ -n "$ADMIN_PASSWORD" ]; then
    if [ "$USE_FORCE" -eq 1 ]; then
        python init_admin.py --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" --force 2>&1 | tee "$LOGFILE"
    else
        python init_admin.py --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" 2>&1 | tee "$LOGFILE"
    fi
else
    if [ "$USE_FORCE" -eq 1 ]; then
        python init_admin.py --email "$ADMIN_EMAIL" --force 2>&1 | tee "$LOGFILE"
    else
        python init_admin.py --email "$ADMIN_EMAIL" 2>&1 | tee "$LOGFILE"
    fi
fi

# capture exit code from the command before tee
RC=${PIPESTATUS[0]}
if [ "$RC" -ne 0 ]; then
    echo "init_admin.py falhou. Veja o log: $LOGFILE"
    exit $RC
fi

echo ""
echo "=== Build concluido com sucesso! ==="