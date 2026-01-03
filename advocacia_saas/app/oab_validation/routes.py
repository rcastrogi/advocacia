"""
API endpoint para validação de OAB
"""

from flask import Blueprint, jsonify, request

from app import limiter
from app.decorators import validate_with_schema
from app.schemas import OABValidationSchema
from app.utils.error_messages import format_error_for_user
from app.utils.oab_validator import consultar_oab_online, validar_oab_com_nome

bp = Blueprint("oab_validation", __name__, url_prefix="/api/oab")


@bp.route("/validar", methods=["POST"])
@limiter.limit("10 per minute")
@validate_with_schema(OABValidationSchema, location="json")
def validar_oab():
    """
    Endpoint para validar número OAB

    POST /api/oab/validar
    Body: {
        "oab_number": "123456",
        "state": "SP",
        "name": "João Silva" (opcional)
    }

    Returns:
        JSON com resultado da validação
    """
    try:
        data = request.validated_data
        numero_oab = data.get("oab_number")
        state = data.get("state")
        nome = data.get("name")

        full_oab = f"{state}{numero_oab}"

        if nome:
            resultado = validar_oab_com_nome(full_oab, nome)
        else:
            resultado = consultar_oab_online(full_oab)

        status_code = 200 if resultado.get("formato_valido") else 400

        return jsonify(resultado), status_code
    except Exception as e:
        error_msg = format_error_for_user(e, "Erro ao validar OAB")
        return jsonify({"error": error_msg}), 500


@bp.route("/validar/<numero_oab>", methods=["GET"])
def validar_oab_get(numero_oab):
    """
    Endpoint GET para validação rápida de OAB

    GET /api/oab/validar/SP123456

    Returns:
        JSON com resultado da validação
    """
    resultado = consultar_oab_online(numero_oab)
    status_code = 200 if resultado["formato_valido"] else 400

    return jsonify(resultado), status_code
