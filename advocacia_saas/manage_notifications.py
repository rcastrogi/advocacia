#!/usr/bin/env python3
"""
Script para gerenciamento de notificações de processos.
Executa verificações periódicas e manutenção do sistema de notificações.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.processes.notifications import run_notification_checks


def main():
    """Função principal do script de notificações."""

    app = create_app()

    with app.app_context():
        print("🔄 Executando verificações de notificações...")

        try:
            notifications_created = run_notification_checks()
            print(
                f"✅ Verificações concluídas! {notifications_created} notificações criadas."
            )

        except Exception as e:
            print(f"❌ Erro durante verificações: {str(e)}")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
