"""
Módulo de Procurações
"""

from flask import Blueprint

bp = Blueprint("procuracao", __name__)

from app.procuracao import routes
