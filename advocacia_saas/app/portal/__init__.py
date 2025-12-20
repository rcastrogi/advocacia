"""
Blueprint do Portal do Cliente
"""

from flask import Blueprint

bp = Blueprint("portal", __name__, url_prefix="/portal")

from app.portal import routes
