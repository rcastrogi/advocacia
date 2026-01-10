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
    """Configura logging robusto para capturar erros em produção"""

    # Criar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # INFO em produção, não DEBUG

    # HANDLER 1: Console (stdout) - Apenas INFO e acima
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # HANDLER 2: Arquivo de log DESABILITADO (para não estourar espaço do servidor)
    # Logs são enviados apenas para stdout (console) e capturados pelo Render
    pass

    # Configurar loggers específicos - NÍVEIS APROPRIADOS PARA PRODUÇÃO
    logging.getLogger("flask").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)  # WARNING - não DEBUG!
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

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
    print("✅ LOGGING INICIALIZADO - MODO PRODUÇÃO")
    print("=" * 70)
    print(f"   🔹 Console: ATIVADO (stdout)")
    print(f"   🔹 Nível: INFO (produção)")
    print("   🔹 SQLAlchemy: WARNING (otimizado)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    setup_production_logging()
    logging.info("Teste de logging inicializado")
