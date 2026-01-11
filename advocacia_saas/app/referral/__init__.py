"""
Módulo do Programa de Indicação
Sistema de referências com recompensas para usuários
"""

from flask import Blueprint

bp = Blueprint("referral", __name__, url_prefix="/referral")

from app.referral import routes  # noqa
