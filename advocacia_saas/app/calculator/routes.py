"""
Rotas da Calculadora Jurídica
Utiliza API do Banco Central do Brasil para índices reais
"""

from datetime import datetime
from decimal import Decimal

from flask import jsonify, render_template, request
from flask_login import login_required

from app import limiter
from app.calculator import bp
from app.calculator.services import (
    CalculoCompletoService,
    CorrecaoMonetariaService,
    HonorariosService,
    IndicesService,
    JurosService,
)
from app.rate_limits import AUTH_API_LIMIT


@bp.route("/")
@login_required
def index():
    """Página principal da calculadora jurídica"""
    indices = IndicesService.obter_indices()
    taxas_juros = IndicesService.get_taxas_juros()

    return render_template(
        "calculator/index.html", indices=indices, taxas_juros=taxas_juros
    )


@bp.route("/api/indices", methods=["GET"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def api_indices():
    """API para obter índices atualizados do BCB"""
    try:
        indices = IndicesService.obter_indices()
        return jsonify(
            {
                "success": True,
                "indices": indices,
                "fonte": "Banco Central do Brasil",
                "atualizado_em": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify(
            {"success": False, "message": f"Erro ao buscar índices: {str(e)}"}
        ), 500


@bp.route("/api/correcao-monetaria", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def calcular_correcao():
    """API para cálculo de correção monetária com dados reais do BCB"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    try:
        valor = Decimal(str(data.get("valor", 0)))
        data_inicial = data.get("data_inicial")
        data_final = data.get("data_final")
        indice = data.get("indice", "IPCA")

        if not data_inicial or not data_final:
            return jsonify({"success": False, "message": "Datas são obrigatórias"}), 400

        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_final = datetime.strptime(data_final, "%Y-%m-%d")

        resultado = CorrecaoMonetariaService.calcular(
            valor=valor,
            data_inicial=dt_inicial,
            data_final=dt_final,
            indice=indice,
        )

        if not resultado.sucesso:
            return jsonify({"success": False, "message": resultado.erro}), 400

        return jsonify({"success": True, "resultado": resultado.resultado})

    except ValueError as e:
        return jsonify({"success": False, "message": f"Erro nos dados: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro no cálculo: {str(e)}"}), 500


@bp.route("/api/juros", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def calcular_juros():
    """API para cálculo de juros"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    try:
        valor_principal = Decimal(str(data.get("valor", 0)))
        data_inicial = data.get("data_inicial")
        data_final = data.get("data_final")
        tipo_juros = data.get("tipo_juros", "mora_civil")
        taxa_customizada = data.get("taxa_customizada")
        capitalizado = data.get("capitalizado", False)

        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_final = datetime.strptime(data_final, "%Y-%m-%d")

        taxa = Decimal(str(taxa_customizada)) if taxa_customizada else None

        resultado = JurosService.calcular(
            valor_principal=valor_principal,
            data_inicial=dt_inicial,
            data_final=dt_final,
            tipo_juros=tipo_juros,
            taxa_customizada=taxa,
            capitalizado=capitalizado,
        )

        if not resultado.sucesso:
            return jsonify({"success": False, "message": resultado.erro}), 400

        return jsonify({"success": True, "resultado": resultado.resultado})

    except Exception as e:
        return jsonify({"success": False, "message": f"Erro no cálculo: {str(e)}"}), 500


@bp.route("/api/honorarios", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def calcular_honorarios():
    """API para cálculo de honorários advocatícios"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    try:
        valor_causa = Decimal(str(data.get("valor_causa", 0)))
        tipo_honorario = data.get("tipo_honorario", "contratual")
        percentual = Decimal(str(data.get("percentual", 20)))
        valor_fixo = Decimal(str(data.get("valor_fixo", 0)))
        sucumbencia_min = Decimal(str(data.get("sucumbencia_min", 10)))
        sucumbencia_max = Decimal(str(data.get("sucumbencia_max", 20)))
        percentual_exitum = Decimal(str(data.get("percentual_exitum", 30)))

        resultado = HonorariosService.calcular(
            valor_causa=valor_causa,
            tipo_honorario=tipo_honorario,
            percentual=percentual,
            valor_fixo=valor_fixo,
            sucumbencia_min=sucumbencia_min,
            sucumbencia_max=sucumbencia_max,
            percentual_exitum=percentual_exitum,
        )

        return jsonify({"success": True, "resultado": resultado.resultado})

    except Exception as e:
        return jsonify({"success": False, "message": f"Erro no cálculo: {str(e)}"}), 500


@bp.route("/api/completo", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def calcular_completo():
    """API para cálculo completo: correção + juros usando API do BCB"""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400

    try:
        valor_original = Decimal(str(data.get("valor", 0)))
        data_inicial = data.get("data_inicial")
        data_final = data.get("data_final")
        indice = data.get("indice", "IPCA")
        tipo_juros = data.get("tipo_juros", "mora_civil")
        aplicar_juros = data.get("aplicar_juros", True)

        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_final = datetime.strptime(data_final, "%Y-%m-%d")

        resultado = CalculoCompletoService.calcular(
            valor_original=valor_original,
            data_inicial=dt_inicial,
            data_final=dt_final,
            indice=indice,
            tipo_juros=tipo_juros,
            aplicar_juros=aplicar_juros,
        )

        if not resultado.sucesso:
            return jsonify({"success": False, "message": resultado.erro}), 400

        return jsonify({"success": True, "resultado": resultado.resultado})

    except Exception as e:
        return jsonify({"success": False, "message": f"Erro no cálculo: {str(e)}"}), 500
