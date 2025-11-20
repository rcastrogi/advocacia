@echo off
echo ========================================
echo   PETITIO - Deploy para Render.com
echo ========================================
echo.

REM Navegar para o diretório do projeto
cd /d F:\PROJETOS\advocacia\advocacia_saas

echo [1/7] Verificando Git...
git --version
if errorlevel 1 (
    echo ERRO: Git nao encontrado!
    echo Instale o Git em: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo OK!
echo.

echo [2/7] Inicializando repositorio Git...
git init
if errorlevel 1 (
    echo Repositorio ja existe, continuando...
)
echo OK!
echo.

echo [3/7] Configurando Git (substitua pelos seus dados)...
git config user.name "Seu Nome"
git config user.email "seu.email@example.com"
echo OK!
echo.

echo [4/7] Adicionando arquivos...
git add .
echo OK!
echo.

echo [5/7] Criando commit inicial...
git commit -m "Initial commit - Petitio v1.0"
if errorlevel 1 (
    echo Nenhuma alteracao para commitar ou ja existe commit
)
echo OK!
echo.

echo [6/7] Verificando status...
git status
echo.

echo ========================================
echo   PROXIMO PASSO:
echo ========================================
echo.
echo 1. Crie um repositorio no GitHub:
echo    https://github.com/new
echo.
echo 2. Nome: petitio
echo    Descricao: Sistema de Gestao para Advogados
echo    NAO marque "Initialize with README"
echo.
echo 3. Execute este comando (substitua SEU_USUARIO):
echo.
echo    git remote add origin https://github.com/SEU_USUARIO/petitio.git
echo    git branch -M main
echo    git push -u origin main
echo.
echo 4. Depois acesse:
echo    https://dashboard.render.com
echo    New + ^> Blueprint
echo    Conecte seu repositorio
echo.
echo ========================================

pause
