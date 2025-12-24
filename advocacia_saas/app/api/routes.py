import requests
from config import Config
from flask import jsonify, request
from flask_login import current_user, login_required

from app.api import bp
from app.models import Cidade, Client, Estado, User


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
def get_estados():
    """Get all Brazilian states"""
    try:
        estados = Estado.query.order_by(Estado.nome).all()
        return jsonify([estado.to_dict() for estado in estados])
    except Exception:
        return jsonify({"error": "Erro ao buscar estados"}), 500


@bp.route("/estados/<sigla>/cidades")
def get_cidades_by_estado(sigla):
    """Get cities by state"""
    try:
        estado = Estado.query.filter_by(sigla=sigla.upper()).first()
        if not estado:
            return jsonify({"error": "Estado não encontrado"}), 404

        cidades = (
            Cidade.query.filter_by(estado_id=estado.id).order_by(Cidade.nome).all()
        )
        return jsonify([cidade.to_dict() for cidade in cidades])
    except Exception:
        return jsonify({"error": "Erro ao buscar cidades"}), 500


@bp.route("/cep/<cep>")
def get_cep_info(cep):
    """Get address information from CEP using ViaCEP API"""
    try:
        # Remove any non-numeric characters
        clean_cep = "".join(filter(str.isdigit, cep))

        if len(clean_cep) != 8:
            return jsonify({"error": "CEP deve conter 8 dígitos"}), 400

        # Format CEP
        formatted_cep = f"{clean_cep[:5]}-{clean_cep[5:]}"

        # Call ViaCEP API
        response = requests.get(Config.CEP_API_URL.format(clean_cep), timeout=10)

        if response.status_code == 200:
            data = response.json()

            # Check if CEP was found
            if "erro" in data:
                return jsonify({"error": "CEP não encontrado"}), 404

            return jsonify(
                {
                    "cep": formatted_cep,
                    "street": data.get("logradouro", ""),
                    "neighborhood": data.get("bairro", ""),
                    "city": data.get("localidade", ""),
                    "uf": data.get("uf", ""),
                    "complement": data.get("complemento", ""),
                }
            )
        else:
            return jsonify({"error": "Erro ao consultar CEP"}), 500

    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout na consulta do CEP"}), 500
    except requests.exceptions.RequestException:
        return jsonify({"error": "Erro de conexão ao consultar CEP"}), 500
    except Exception:
        return jsonify({"error": "Erro interno do servidor"}), 500


@bp.route("/clients")
@api_login_required
def get_clients():
    """Get all clients for the current user"""
    try:
        clients = Client.query.filter_by(lawyer_id=current_user.id).all()
        return jsonify([client.to_dict() for client in clients])
    except Exception:
        return jsonify({"error": "Erro ao buscar clientes"}), 500


@bp.route("/clients", methods=["POST"])
@api_login_required
def create_client():
    """Create a new client"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        # Validate required fields
        required_fields = ["full_name", "email", "cpf_cnpj", "mobile_phone"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo {field} é obrigatório"}), 400

        # Check if client with this email already exists for this lawyer
        existing_client = Client.query.filter_by(
            email=data["email"], lawyer_id=current_user.id
        ).first()
        if existing_client:
            return jsonify({"error": "Cliente com este email já existe"}), 400

        # Check if CPF/CNPJ already exists for this lawyer
        existing_cpf = Client.query.filter_by(
            cpf_cnpj=data["cpf_cnpj"], lawyer_id=current_user.id
        ).first()
        if existing_cpf:
            return jsonify({"error": "Cliente com este CPF/CNPJ já existe"}), 400

        client = Client(
            full_name=data["full_name"],
            email=data["email"],
            cpf_cnpj=data["cpf_cnpj"],
            mobile_phone=data["mobile_phone"],
            lawyer_id=current_user.id,
            # Optional fields
            landline_phone=data.get("landline_phone"),
            rg=data.get("rg"),
            civil_status=data.get("civil_status"),
            birth_date=data.get("birth_date"),
            profession=data.get("profession"),
            nationality=data.get("nationality"),
            birth_place=data.get("birth_place"),
            mother_name=data.get("mother_name"),
            father_name=data.get("father_name"),
            address_type=data.get("address_type"),
            cep=data.get("cep"),
            street=data.get("street"),
            number=data.get("number"),
            uf=data.get("uf"),
            city=data.get("city"),
            neighborhood=data.get("neighborhood"),
            complement=data.get("complement"),
        )

        from app import db
        db.session.add(client)
        db.session.commit()

        return jsonify(client.to_dict()), 201

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({"error": f"Erro ao criar cliente: {str(e)}"}), 500


@bp.route("/clients/<int:client_id>")
@api_login_required
def get_client(client_id):
    """Get a specific client by ID"""
    try:
        client = Client.query.filter_by(
            id=client_id, lawyer_id=current_user.id
        ).first()

        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404

        return jsonify(client.to_dict())

    except Exception:
        return jsonify({"error": "Erro ao buscar cliente"}), 500


@bp.route("/clients/<int:client_id>", methods=["PUT"])
@api_login_required
def update_client(client_id):
    """Update a client"""
    try:
        client = Client.query.filter_by(
            id=client_id, lawyer_id=current_user.id
        ).first()

        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404

        data = request.get_json()

        if not data:
            return jsonify({"error": "Dados não fornecidos"}), 400

        # Update fields
        updatable_fields = [
            "full_name", "email", "cpf_cnpj", "mobile_phone", "landline_phone",
            "rg", "civil_status", "birth_date", "profession", "nationality",
            "birth_place", "mother_name", "father_name", "address_type",
            "cep", "street", "number", "uf", "city", "neighborhood", "complement"
        ]

        for field in updatable_fields:
            if field in data:
                setattr(client, field, data[field])

        from app import db
        db.session.commit()

        return jsonify(client.to_dict())

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({"error": f"Erro ao atualizar cliente: {str(e)}"}), 500


@bp.route("/clients/<int:client_id>", methods=["DELETE"])
@api_login_required
def delete_client(client_id):
    """Delete a client"""
    try:
        client = Client.query.filter_by(
            id=client_id, lawyer_id=current_user.id
        ).first()

        if not client:
            return jsonify({"error": "Cliente não encontrado"}), 404

        from app import db
        db.session.delete(client)
        db.session.commit()

        return jsonify({"message": "Cliente deletado com sucesso"})

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({"error": f"Erro ao deletar cliente: {str(e)}"}), 500
