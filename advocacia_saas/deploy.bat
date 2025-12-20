@echo off
echo ====================================
echo  Deploying Petitio to Fly.io
echo ====================================
echo.

cd /d "%~dp0"

echo [1/2] Verificando configuração...
if not exist "fly.toml" (
    echo ERRO: Arquivo fly.toml não encontrado!
    pause
    exit /b 1
)

echo [2/2] Fazendo deploy...
fly deploy --ha=false

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo  Deploy concluído com sucesso!
    echo  Aplicação: https://petitio.fly.dev
    echo ====================================
    echo.
    echo Abrindo logs...
    fly logs
) else (
    echo.
    echo ERRO: Deploy falhou!
    pause
    exit /b 1
)

pause
