"""
API endpoint para validação de OAB
"""

from flask import Blueprint, jsonify, request

from app.utils.oab_validator import consultar_oab_online, validar_oab_com_nome

bp = Blueprint("oab_validation", __name__, url_prefix="/api/oab")


@bp.route("/validar", methods=["POST"])
def validar_oab():
    """
    Endpoint para validar número OAB

    POST /api/oab/validar
    Body: {
        "numero_oab": "SP123456",
        "nome": "João Silva" (opcional)
    }

    Returns:
        JSON com resultado da validação
    """
    data = request.get_json()

    if not data or "numero_oab" not in data:
        return jsonify({"error": "Campo numero_oab é obrigatório"}), 400

    numero_oab = data["numero_oab"]
    nome = data.get("nome")

    if nome:
        resultado = validar_oab_com_nome(numero_oab, nome)
    else:
        resultado = consultar_oab_online(numero_oab)

    status_code = 200 if resultado["formato_valido"] else 400

    return jsonify(resultado), status_code


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
