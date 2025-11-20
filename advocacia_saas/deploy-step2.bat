@echo off
echo ========================================
echo   PETITIO - Conectar ao GitHub
echo ========================================
echo.

REM Navegar para o diretório do projeto
cd /d F:\PROJETOS\advocacia\advocacia_saas

set /p GITHUB_USER="Digite seu usuario do GitHub: "
echo.

echo [1/3] Adicionando repositorio remoto...
git remote add origin https://github.com/%GITHUB_USER%/petitio.git
if errorlevel 1 (
    echo Remoto ja existe, removendo e adicionando novamente...
    git remote remove origin
    git remote add origin https://github.com/%GITHUB_USER%/petitio.git
)
echo OK!
echo.

echo [2/3] Renomeando branch para main...
git branch -M main
echo OK!
echo.

echo [3/3] Enviando para o GitHub...
echo.
echo ATENCAO: Voce precisara fazer login!
echo Use seu usuario e Personal Access Token (NAO senha)
echo.
echo Para criar token: https://github.com/settings/tokens
echo Marque: repo (Full control)
echo.
pause
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ERRO ao fazer push!
    echo Verifique:
    echo 1. Repositorio existe no GitHub?
    echo 2. Usou Personal Access Token?
    echo 3. Token tem permissao 'repo'?
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SUCESSO!
echo ========================================
echo.
echo Codigo enviado para GitHub!
echo.
echo PROXIMO PASSO:
echo.
echo 1. Acesse: https://dashboard.render.com
echo 2. Clique em: New + ^> Blueprint
echo 3. Conecte: GitHub
echo 4. Selecione: petitio
echo 5. Clique: Apply
echo.
echo Aguarde 5-10 minutos para o deploy completar!
echo.
echo ========================================

pause
