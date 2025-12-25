"""
Blueprint para funcionalidades de LGPD (Lei Geral de Proteção de Dados)
"""

from flask import Blueprint

lgpd_bp = Blueprint("lgpd", __name__, url_prefix="/lgpd")

from app.lgpd import routes
