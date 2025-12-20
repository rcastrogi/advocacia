#!/bin/bash
# Script de Deploy para Fly.io - Petitio SaaS
# ============================================

echo "🚀 Iniciando deploy do Petitio no Fly.io..."
echo ""

# 1. Verificar se Fly CLI está instalado
if ! command -v flyctl &> /dev/null; then
    echo "❌ Fly CLI não está instalado!"
    echo "   Instale com: curl -L https://fly.io/install.sh | sh"
    echo "   Ou no Windows: iwr https://fly.io/install.ps1 -useb | iex"
    exit 1
fi

echo "✅ Fly CLI encontrado"

# 2. Fazer login (se necessário)
echo "🔐 Verificando autenticação..."
flyctl auth whoami &> /dev/null || flyctl auth login

# 3. Verificar se app existe
echo "🔍 Verificando se app 'petitio' existe..."
if flyctl apps list | grep -q "petitio"; then
    echo "✅ App 'petitio' encontrado"
else
    echo "⚠️  App 'petitio' não encontrado. Criando..."
    flyctl apps create petitio --org personal
fi

# 4. Configurar secrets (variáveis de ambiente)
echo ""
echo "🔑 Configurando variáveis de ambiente..."
echo "   (você precisará fornecer os valores)"
echo ""

# Ler valores do .env local (se existir)
if [ -f .env ]; then
    echo "📄 Arquivo .env encontrado. Carregando valores..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Configurar secrets no Fly.io
echo "🔐 Configurando SECRET_KEY..."
flyctl secrets set SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}" --app petitio

echo "🔐 Configurando DATABASE_URL..."
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL não encontrada!"
    echo "   Configure manualmente com:"
    echo "   flyctl secrets set DATABASE_URL='postgresql://...' --app petitio"
else
    flyctl secrets set DATABASE_URL="$DATABASE_URL" --app petitio
fi

echo "🔐 Configurando OPENAI_API_KEY..."
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY não encontrada!"
    echo "   Configure manualmente com:"
    echo "   flyctl secrets set OPENAI_API_KEY='sk-...' --app petitio"
else
    flyctl secrets set OPENAI_API_KEY="$OPENAI_API_KEY" --app petitio
fi

echo "🔐 Configurando Mercado Pago..."
if [ -n "$MERCADOPAGO_ACCESS_TOKEN" ]; then
    flyctl secrets set MERCADOPAGO_ACCESS_TOKEN="$MERCADOPAGO_ACCESS_TOKEN" --app petitio
fi

if [ -n "$MERCADOPAGO_PUBLIC_KEY" ]; then
    flyctl secrets set MERCADOPAGO_PUBLIC_KEY="$MERCADOPAGO_PUBLIC_KEY" --app petitio
fi

# 5. Deploy
echo ""
echo "🚀 Iniciando deploy..."
flyctl deploy --app petitio --remote-only

# 6. Verificar status
echo ""
echo "✅ Deploy concluído!"
echo ""
echo "📊 Status da aplicação:"
flyctl status --app petitio

echo ""
echo "🌐 URL da aplicação:"
flyctl apps info petitio | grep Hostname

echo ""
echo "📋 Comandos úteis:"
echo "   Ver logs:        flyctl logs --app petitio"
echo "   Abrir app:       flyctl open --app petitio"
echo "   SSH:             flyctl ssh console --app petitio"
echo "   Escalar:         flyctl scale vm shared-cpu-1x --memory 512 --app petitio"
echo "   Ver secrets:     flyctl secrets list --app petitio"
echo ""
