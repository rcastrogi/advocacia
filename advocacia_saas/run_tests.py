#!/usr/bin/env python3
"""
Sistema de Testes Unitários - Petitio SaaS
==========================================

Este arquivo demonstra como executar os testes de forma organizada.

Estrutura:
- tests/backend/: Testes Python/Flask (pytest)
- tests/frontend/: Testes JavaScript (Jest)
- tests/integration/: Testes de integração
- tests/e2e/: Testes end-to-end (opcional)

Para executar:
    python run_tests.py              # Todos os testes
    python run_tests.py --backend    # Apenas back-end
    python run_tests.py --frontend   # Apenas front-end
    python run_tests.py --coverage   # Com relatório de cobertura
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Cores para output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Imprime aviso"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def run_command(command, cwd=None, description=""):
    """Executa comando e retorna resultado"""
    try:
        print(f"{Colors.BLUE}🔄 {description}{Colors.END}")
        result = subprocess.run(
            command, shell=True, cwd=cwd, capture_output=True, text=True, check=True
        )
        print_success(f"{description} concluído")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"{description} falhou")
        print(f"Erro: {e.stderr}")
        return False, e.stderr


def run_backend_tests(coverage=False):
    """Executa testes back-end"""
    print_header("TESTES BACK-END (Python/Flask)")

    # Verificar se estamos no diretório correto
    if not Path("app").exists():
        print_error(
            "Diretório 'app' não encontrado. Execute este script da raiz do projeto."
        )
        return False

    # Comando base
    cmd = "python -m pytest tests/ -v"

    if coverage:
        cmd += " --cov=app --cov-report=html --cov-report=term-missing"

    success, output = run_command(cmd, description="Executando testes back-end")

    if success and coverage:
        print_success("Relatório de cobertura gerado em htmlcov/index.html")

    return success


def run_frontend_tests(coverage=False):
    """Executa testes front-end"""
    print_header("TESTES FRONT-END (JavaScript)")

    # Verificar se Jest está instalado
    if not Path("node_modules/.bin/jest").exists():
        print_warning("Jest não encontrado. Instalando dependências...")
        success, _ = run_command(
            "npm install", description="Instalando dependências Node.js"
        )
        if not success:
            return False

    # Comando base
    cmd = "npm test"

    if coverage:
        cmd += " -- --coverage"

    success, output = run_command(cmd, description="Executando testes front-end")

    if success and coverage:
        print_success(
            "Relatório de cobertura gerado em coverage/lcov-report/index.html"
        )

    return success


def run_integration_tests():
    """Executa testes de integração"""
    print_header("TESTES DE INTEGRAÇÃO")

    cmd = "python -m pytest tests/integration/ -v --tb=short"
    success, output = run_command(cmd, description="Executando testes de integração")

    return success


def run_all_tests(coverage=False):
    """Executa todos os testes"""
    print_header("EXECUTANDO TODOS OS TESTES")

    results = []

    # Back-end
    backend_success = run_backend_tests(coverage)
    results.append(("Back-end", backend_success))

    # Front-end
    frontend_success = run_frontend_tests(coverage)
    results.append(("Front-end", frontend_success))

    # Integração
    integration_success = run_integration_tests()
    results.append(("Integração", integration_success))

    # Resumo
    print_header("RESUMO DOS TESTES")

    all_passed = True
    for name, success in results:
        status = "PASSOU" if success else "FALHOU"
        color = Colors.GREEN if success else Colors.RED
        print(f"{name}: {color}{status}{Colors.END}")
        if not success:
            all_passed = False

    if all_passed:
        print_success("🎉 Todos os testes passaram!")
        return True
    else:
        print_error("💥 Alguns testes falharam. Verifique os logs acima.")
        return False


def setup_test_environment():
    """Configura ambiente de testes"""
    print_header("CONFIGURANDO AMBIENTE DE TESTES")

    # Verificar se estamos no diretório correto
    if not Path("app").exists():
        print_error("Execute este script da raiz do projeto Petitio.")
        return False

    # Verificar Python
    success, _ = run_command("python --version", description="Verificando Python")
    if not success:
        return False

    # Verificar pip
    success, _ = run_command("pip --version", description="Verificando pip")
    if not success:
        return False

    # Instalar dependências Python se necessário
    if not Path("venv").exists():
        print_warning("Virtual environment não encontrado. Criando...")
        success, _ = run_command(
            "python -m venv venv", description="Criando virtual environment"
        )
        if not success:
            return False

    # Ativar venv e instalar dependências
    activate_cmd = (
        ". venv/bin/activate" if os.name != "nt" else "venv\\Scripts\\activate"
    )
    install_cmd = f"{activate_cmd} && pip install -r requirements.txt pytest pytest-cov"

    success, _ = run_command(install_cmd, description="Instalando dependências Python")
    if not success:
        return False

    # Verificar Node.js (opcional para front-end)
    try:
        success, _ = run_command("node --version", description="Verificando Node.js")
        if success:
            # Instalar dependências Node.js se package.json existir
            if Path("package.json").exists():
                success, _ = run_command(
                    "npm install", description="Instalando dependências Node.js"
                )
    except:
        print_warning("Node.js não encontrado. Testes front-end serão pulados.")

    print_success("Ambiente de testes configurado com sucesso!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sistema de Testes Unitários - Petitio SaaS"
    )
    parser.add_argument(
        "--backend", action="store_true", help="Executar apenas testes back-end"
    )
    parser.add_argument(
        "--frontend", action="store_true", help="Executar apenas testes front-end"
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Executar apenas testes de integração",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Gerar relatório de cobertura"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Configurar ambiente de testes"
    )

    args = parser.parse_args()

    # Configurar ambiente se solicitado
    if args.setup:
        if not setup_test_environment():
            sys.exit(1)
        return

    # Executar testes específicos ou todos
    if args.backend:
        success = run_backend_tests(args.coverage)
    elif args.frontend:
        success = run_frontend_tests(args.coverage)
    elif args.integration:
        success = run_integration_tests()
    else:
        success = run_all_tests(args.coverage)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
