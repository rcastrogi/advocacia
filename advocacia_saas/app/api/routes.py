import requests
from config import Config
from flask import jsonify, request

from app.api import bp
from app.models import Estado, Cidade


@bp.route("/estados")
def get_estados():
    """Get all Brazilian states"""
    try:
        estados = Estado.query.order_by(Estado.nome).all()
        return jsonify([estado.to_dict() for estado in estados])
    except Exception as e:
        return jsonify({"error": "Erro ao buscar estados"}), 500


@bp.route("/estados/<sigla>/cidades")
def get_cidades_by_estado(sigla):
    """Get cities by state"""
    try:
        estado = Estado.query.filter_by(sigla=sigla.upper()).first()
        if not estado:
            return jsonify({"error": "Estado não encontrado"}), 404
        
        cidades = Cidade.query.filter_by(estado_id=estado.id).order_by(Cidade.nome).all()
        return jsonify([cidade.to_dict() for cidade in cidades])
    except Exception as e:
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
    except Exception as e:
        return jsonify({"error": "Erro interno do servidor"}), 500
