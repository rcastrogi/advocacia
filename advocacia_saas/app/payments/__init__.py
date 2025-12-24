"""
Blueprint de pagamentos - Mercado Pago
"""

from flask import Blueprint

bp = Blueprint("payments", __name__, url_prefix="/payments")

from app.payments import routes
