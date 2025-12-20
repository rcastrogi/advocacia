# Script de Deploy para Fly.io - Petitio SaaS (Windows PowerShell)
# ====================================================================

Write-Host "🚀 Iniciando deploy do Petitio no Fly.io..." -ForegroundColor Green
Write-Host ""

# Verificar se Fly CLI está instalado
$flyctlPath = Get-Command flyctl -ErrorAction SilentlyContinue
if (-not $flyctlPath) {
    Write-Host "❌ Fly CLI não está instalado!" -ForegroundColor Red
    Write-Host "   Instale com: iwr https://fly.io/install.ps1 -useb | iex" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Fly CLI encontrado" -ForegroundColor Green

# Verificar autenticação
Write-Host "🔐 Verificando autenticação..." -ForegroundColor Cyan
$authStatus = flyctl auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Não está autenticado. Fazendo login..." -ForegroundColor Yellow
    flyctl auth login
}

# Deploy
Write-Host ""
Write-Host "🚀 Fazendo deploy das mudanças..." -ForegroundColor Green
Write-Host ""
flyctl deploy --app petitio --remote-only

# Verificar status
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Deploy concluído com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Status da aplicação:" -ForegroundColor Cyan
    flyctl status --app petitio
    
    Write-Host ""
    Write-Host "🌐 Acessar aplicação:" -ForegroundColor Cyan
    Write-Host "   flyctl open --app petitio" -ForegroundColor White
    
    Write-Host ""
    Write-Host "📋 Comandos úteis:" -ForegroundColor Yellow
    Write-Host "   Ver logs:        flyctl logs --app petitio" -ForegroundColor White
    Write-Host "   Ver logs (tail): flyctl logs --app petitio -f" -ForegroundColor White
    Write-Host "   SSH console:     flyctl ssh console --app petitio" -ForegroundColor White
    Write-Host "   Reiniciar:       flyctl apps restart petitio" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Deploy falhou! Verifique os logs acima." -ForegroundColor Red
    Write-Host "   Ver logs: flyctl logs --app petitio" -ForegroundColor Yellow
}

Write-Host ""

