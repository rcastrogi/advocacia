"""
Blueprint de Gerenciamento de Documentos
"""

from flask import Blueprint

bp = Blueprint("documents", __name__, url_prefix="/documents")

from app.documents import routes
