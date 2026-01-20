"""
Rotas da API geral
"""

from flask import get_flashed_messages, jsonify, request
from flask_login import current_user

from app import limiter
from app.api import bp
from app.api.services import CEPService, CidadeService, ClientAPIService, EstadoService


def api_login_required(f):
    """Decorator for API routes that returns 401 instead of redirecting."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/estados")
@limiter.limit("100 per hour")
def get_estados():
    """Get all Brazilian states"""
    try:
        estados = EstadoService.listar_todos()
        return jsonify(estados)
    except Exception:
        return jsonify({"error": "Erro ao buscar estados"}), 500


@bp.route("/estados/<sigla>/cidades")
@limiter.limit("100 per hour")
def get_cidades_by_estado(sigla):
    """Get cities by state"""
    resultado = CidadeService.listar_por_estado(sigla)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data)


@bp.route("/cep/<cep>")
@limiter.limit("50 per hour")
def get_cep_info(cep):
    """Get address information from CEP using ViaCEP API"""
    resultado = CEPService.consultar(cep)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data)


@bp.route("/clients")
@api_login_required
@limiter.limit("200 per hour")
def get_clients():
    """Get all clients for the current user"""
    try:
        clients = ClientAPIService.listar(current_user.id)
        return jsonify(clients)
    except Exception:
        return jsonify({"error": "Erro ao buscar clientes"}), 500


@bp.route("/clients", methods=["POST"])
@api_login_required
@limiter.limit("50 per hour")
def create_client():
    """Create a new client"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400

    resultado = ClientAPIService.criar(current_user.id, data)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data), resultado.status_code


@bp.route("/clients/<int:client_id>")
@api_login_required
@limiter.limit("200 per hour")
def get_client(client_id):
    """Get a specific client by ID"""
    resultado = ClientAPIService.obter(client_id, current_user.id)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data)


@bp.route("/clients/<int:client_id>", methods=["PUT"])
@api_login_required
@limiter.limit("50 per hour")
def update_client(client_id):
    """Update a client"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400

    resultado = ClientAPIService.atualizar(client_id, current_user.id, data)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data)


@bp.route("/clients/<int:client_id>", methods=["DELETE"])
@api_login_required
@limiter.limit("20 per hour")
def delete_client(client_id):
    """Delete a client"""
    resultado = ClientAPIService.deletar(client_id, current_user.id)

    if not resultado.success:
        return jsonify({"error": resultado.error}), resultado.status_code

    return jsonify(resultado.data)


@bp.route("/flash-messages")
def get_flash_messages_api():
    """Get flash messages for the current session"""
    try:
        messages = get_flashed_messages(with_categories=True)
        formatted_messages = []

        for category, message in messages:
            msg_type = "success"
            if category in ["error", "danger"]:
                msg_type = "error"
            elif category == "warning":
                msg_type = "warning"
            elif category == "info":
                msg_type = "info"

            formatted_messages.append({"type": msg_type, "message": message})

        return jsonify(formatted_messages)
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar mensagens: {str(e)}"}), 500

