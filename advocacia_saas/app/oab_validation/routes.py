"""
API endpoint para validação de OAB
"""

from flask import Blueprint, jsonify, request

from app import limiter
from app.decorators import validate_with_schema
from app.oab_validation.services import OABValidationService
from app.schemas import OABValidationSchema

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
        "state": "SP"
    }

    Returns:
        JSON com resultado da validação
    """
    data = request.validated_data
    numero_oab = data.get("oab_number")
    state = data.get("state")

    resultado = OABValidationService.validate(numero_oab, state)

    if resultado.valid:
        return jsonify(
            {
                "valid": True,
                "numero": resultado.numero,
                "uf": resultado.uf,
                "nome": resultado.nome,
                "situacao": resultado.situacao,
                "oab_formatada": OABValidationService.format_oab(
                    resultado.numero, resultado.uf
                ),
            }
        )

    return jsonify({"valid": False, "error": resultado.error}), 400


@bp.route("/validar/<numero_oab>", methods=["GET"])
@limiter.limit("10 per minute")
def validar_oab_get(numero_oab):
    """
    Endpoint GET para validação rápida de OAB

    GET /api/oab/validar/SP123456

    Returns:
        JSON com resultado da validação
    """
    # Extrair UF dos primeiros 2 caracteres
    if len(numero_oab) < 3:
        return jsonify({"valid": False, "error": "Formato inválido"}), 400

    uf = numero_oab[:2].upper()
    numero = numero_oab[2:]

    resultado = OABValidationService.validate(numero, uf)

    if resultado.valid:
        return jsonify(
            {
                "valid": True,
                "numero": resultado.numero,
                "uf": resultado.uf,
                "nome": resultado.nome,
                "situacao": resultado.situacao,
            }
        )

    return jsonify({"valid": False, "error": resultado.error}), 400

