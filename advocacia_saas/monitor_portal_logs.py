#!/usr/bin/env python3
"""
Monitor de logs do portal do cliente
"""

import os
import sys
import time
from datetime import datetime


def monitor_portal_logs():
    """Monitora o arquivo de log do portal em tempo real"""

    log_file = os.path.join(os.path.dirname(__file__), "logs", "portal.log")

    if not os.path.exists(log_file):
        print(f"Arquivo de log não encontrado: {log_file}")
        print("Execute algumas ações no portal para gerar logs.")
        return

    print("=== MONITOR DE LOGS DO PORTAL DO CLIENTE ===")
    print(f"Monitorando: {log_file}")
    print("Pressione Ctrl+C para parar...")
    print("-" * 60)

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            # Ir para o final do arquivo
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    # Formatar a saída
                    if "ERROR" in line:
                        print(f"\033[91m{line.strip()}\033[0m")  # Vermelho para erros
                    elif "WARNING" in line:
                        print(f"\033[93m{line.strip()}\033[0m")  # Amarelo para avisos
                    elif "INFO" in line:
                        print(f"\033[92m{line.strip()}\033[0m")  # Verde para info
                    elif "DEBUG" in line:
                        print(f"\033[94m{line.strip()}\033[0m")  # Azul para debug
                    else:
                        print(line.strip())
                else:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nMonitoramento interrompido pelo usuário.")
    except Exception as e:
        print(f"Erro ao monitorar logs: {e}")


def show_recent_logs(lines=20):
    """Mostra as últimas linhas do log"""

    log_file = os.path.join(os.path.dirname(__file__), "logs", "portal.log")

    if not os.path.exists(log_file):
        print(f"Arquivo de log não encontrado: {log_file}")
        return

    print(f"=== ÚLTIMAS {lines} LINHAS DO LOG DO PORTAL ===")

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            for line in recent_lines:
                line = line.strip()
                if "ERROR" in line:
                    print(f"\033[91m{line}\033[0m")  # Vermelho
                elif "WARNING" in line:
                    print(f"\033[93m{line}\033[0m")  # Amarelo
                elif "INFO" in line:
                    print(f"\033[92m{line}\033[0m")  # Verde
                elif "DEBUG" in line:
                    print(f"\033[94m{line}\033[0m")  # Azul
                else:
                    print(line)

    except Exception as e:
        print(f"Erro ao ler logs: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--recent":
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_recent_logs(lines)
    else:
        monitor_portal_logs()
