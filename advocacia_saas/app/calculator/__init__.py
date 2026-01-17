"""
Calculadora Jurídica - Petitio
Módulo para cálculos jurídicos: correção monetária, juros e honorários
"""

from flask import Blueprint

bp = Blueprint("calculator", __name__, url_prefix="/calculadora")

from app.calculator import routes  # noqa: E402, F401
