@echo off
echo ====================================
echo  Verificando Status - Petitio
echo ====================================
echo.

cd /d "%~dp0"

echo [1/3] Status da aplicação...
fly status

echo.
echo [2/3] Máquinas ativas...
fly machine list

echo.
echo [3/3] Últimos logs...
fly logs --limit 100

pause
