"""
Integração com Stripe para pagamentos
"""

from flask import Blueprint

bp = Blueprint("stripe_integration", __name__)

from app.stripe_integration import routes
