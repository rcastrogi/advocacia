#!/usr/bin/env python3
"""
Script para testar o logging do portal do cliente
"""

import os
import sys
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_portal_logging():
    """Testa o sistema de logging do portal"""

    # Configurar logging igual ao do portal
    portal_logger = logging.getLogger('portal_test')
    portal_logger.setLevel(logging.DEBUG)

    # Criar handler para arquivo
    log_file = os.path.join(os.path.dirname(__file__), 'logs', 'portal_test.log')
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    # Criar formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)

    # Adicionar handler ao logger
    if not portal_logger.handlers:
        portal_logger.addHandler(file_handler)

    # Testar diferentes tipos de log
    portal_logger.info("=== INÍCIO DOS TESTES DE LOGGING DO PORTAL ===")
    portal_logger.info("Testando sistema de logging do portal do cliente")

    # Simular acesso ao dashboard
    portal_logger.info("Usuário teste@example.com acessando dashboard do portal")
    portal_logger.debug("Cliente encontrado: ID 123 - João Silva")

    # Simular erro
    try:
        # Simular um erro que pode acontecer
        result = 1 / 0
    except ZeroDivisionError as e:
        portal_logger.error(f"Erro de divisão por zero simulado: {str(e)}")
        portal_logger.error("Traceback: ZeroDivisionError: division by zero")

    # Simular upload
    portal_logger.info("Usuário teste@example.com fazendo upload de documento")
    portal_logger.debug("Arquivo seguro: contrato.pdf, tipo: application/pdf")
    portal_logger.debug("Arquivo salvo: uploads/portal/123/contrato.pdf, tamanho: 1024000 bytes")
    portal_logger.info("Upload bem-sucedido: contrato.pdf para cliente 123")

    # Simular acesso ao chat
    portal_logger.info("Usuário teste@example.com acessando chat")
    portal_logger.debug("Cliente encontrado para chat: 123")
    portal_logger.debug("5 mensagens encontradas na sala 456")

    # Simular erro de API
    portal_logger.error("Erro na API do chat: dados JSON inválidos")
    portal_logger.error("Traceback: JSONDecodeError: Expecting ',' delimiter: line 1 column 10")

    portal_logger.info("=== FIM DOS TESTES DE LOGGING DO PORTAL ===")

    print(f"Logs gerados em: {log_file}")
    print("Verifique o arquivo para ver os logs detalhados.")

if __name__ == "__main__":
    test_portal_logging()