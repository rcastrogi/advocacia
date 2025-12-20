"""
Blueprint de prazos e alertas
"""

from flask import Blueprint

bp = Blueprint("deadlines", __name__, url_prefix="/deadlines")

from app.deadlines import routes
