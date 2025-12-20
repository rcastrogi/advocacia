"""
Blueprint de Chat com Cliente
"""

from flask import Blueprint

bp = Blueprint("chat", __name__, url_prefix="/chat")

from app.chat import events, routes
