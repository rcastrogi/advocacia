#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de logging centralizado para diagnosticar problemas em produção
Captura TODOS os erros e os exibe no console/logs
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime


def setup_production_logging():
    """Configura logging robusto para capturar TUDO em produção"""

    # Criar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # HANDLER 1: Console (stdout) - TUDO vai pra console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # HANDLER 2: Arquivo de log DESABILITADO (para não estourar espaço do servidor)
    # Logs são enviados apenas para stdout (console) e capturados pelo Render
    pass

    # Configurar loggers específicos
    logging.getLogger("flask").setLevel(logging.DEBUG)
    logging.getLogger("sqlalchemy").setLevel(logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.DEBUG)

    # Capturar exceções não tratadas
    def log_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.critical(
            "EXCEÇÃO NÃO TRATADA", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = log_unhandled_exception

    print("\n" + "=" * 70)
    print("✅ LOGGING INICIALIZADO COM SUCESSO")
    print("=" * 70)
    print(f"   🔹 Console: ATIVADO (stdout - capturado pelo Render)")
    print(f"   🔹 Arquivo: DESABILITADO (para preservar espaço do servidor)")
    print(f"   🔹 Nível: DEBUG (captura TUDO)")
    print("   🔹 SQLAlchemy: DEBUG ATIVADO")
    print("   🔹 Werkzeug: DEBUG ATIVADO")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    setup_production_logging()
    logging.info("Teste de logging inicializado")
