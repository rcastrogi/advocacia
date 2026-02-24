@echo off
REM ============================================
REM Build script para o Petitio Assinador
REM ============================================
echo.
echo === Petitio Assinador - Build ===
echo.

REM Verificar Python
python --version 2>nul || (
    echo ERRO: Python nao encontrado no PATH.
    echo Instale Python 3.10+ de https://python.org
    pause
    exit /b 1
)

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)

REM Instalar PyInstaller
pip install pyinstaller

REM Build
echo.
echo Gerando executavel...
pyinstaller petitio_assinador.spec --clean
if errorlevel 1 (
    echo ERRO ao gerar executavel.
    pause
    exit /b 1
)

echo.
echo ============================================
echo BUILD CONCLUIDO!
echo Executavel em: dist\PetitioAssinador\PetitioAssinador.exe
echo ============================================
echo.
pause
