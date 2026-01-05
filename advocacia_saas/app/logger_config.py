"""
Sistema de logging centralizado para toda a aplicação
Garante que logs apareçam no Render e no console local
"""
import sys
import logging
from datetime import datetime

# Handler customizado que escreve direto em STDERR (garantido no Render)
class StderrHandler(logging.StreamHandler):
    """Handler que escreve em sys.stderr com flush automático"""
    def __init__(self):
        super().__init__(sys.stderr)
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + '\n')
            self.stream.flush()  # Força flush imediato
        except Exception:
            self.handleError(record)


def setup_logging(app):
    """
    Configura logging centralizado para toda a aplicação
    
    Uso:
        from app.logger_config import setup_logging
        setup_logging(app)
    
    Depois em qualquer lugar:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Mensagem")
        logger.error("Erro")
    """
    
    # Remover handlers existentes de Flask
    app.logger.handlers.clear()
    
    # Criar formato com timestamp
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler customizado para STDERR
    stderr_handler = StderrHandler()
    stderr_handler.setFormatter(formatter)
    
    # Configurar logger da aplicação
    app.logger.addHandler(stderr_handler)
    app.logger.setLevel(logging.INFO)
    
    # Configurar loggers importantes
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Aplicação
    logging.getLogger('app').setLevel(logging.DEBUG)
    
    # Garantir que todos usam STDERR
    for logger_name in ['app', 'app.decorators', 'app.admin', 'werkzeug']:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(stderr_handler)
        logger.propagate = False
    
    app.logger.info("✅ Sistema de logging inicializado")
