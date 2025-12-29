#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de imports para o sistema de processos
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Testa se todos os módulos podem ser importados sem erros"""
    try:
        # Testar modelos
        from app.models import Process, ProcessNotification

        print("✓ Modelos Process e ProcessNotification importados com sucesso")

        # Testar blueprint
        from app.processes import bp as processes_bp

        print("✓ Blueprint processes importado com sucesso")

        # Testar rotas
        from app.processes.routes import *

        print("✓ Rotas do processes importadas com sucesso")

        # Testar API
        from app.processes.api import *

        print("✓ API do processes importada com sucesso")

        # Testar notificações
        from app.processes.notifications import *

        print("✓ Notificações do processes importadas com sucesso")

        # Testar relatórios
        from app.processes.reports import *

        print("✓ Relatórios do processes importados com sucesso")

        return True

    except Exception as e:
        print(f"✗ Erro ao importar: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
