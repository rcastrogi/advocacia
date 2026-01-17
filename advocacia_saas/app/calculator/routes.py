"""
Rotas da Calculadora Jurídica
Utiliza API do Banco Central do Brasil para índices reais
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from flask import render_template, request, jsonify
from flask_login import login_required

from app.calculator import bp
from app import limiter
from app.rate_limits import AUTH_API_LIMIT
from app.services.bcb_api import (
    calcular_fator_correcao, 
    obter_indices_atuais
)


# Taxas de juros legais (fixas por lei)
TAXAS_JUROS = {
    "mora_civil": {
        "nome": "Juros Moratórios - Código Civil",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "Art. 406, CC c/c Art. 161, §1º, CTN"
    },
    "mora_trabalhista": {
        "nome": "Juros Moratórios - Trabalhista",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "Art. 39, §1º, Lei 8.177/91"
    },
    "selic": {
        "nome": "Taxa SELIC (via API BCB)",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "EC 113/2021 - Fazenda Pública"
    }
}


@bp.route("/")
@login_required
def index():
    """Página principal da calculadora jurídica"""
    # Buscar índices atualizados do BCB
    indices = obter_indices_atuais()
    
    return render_template(
        "calculator/index.html",
        indices=indices,
        taxas_juros=TAXAS_JUROS
    )


@bp.route("/api/indices", methods=["GET"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def api_indices():
    """API para obter índices atualizados do BCB"""
    try:
        indices = obter_indices_atuais()
        return jsonify({
            "success": True,
            "indices": indices,
            "fonte": "Banco Central do Brasil",
            "atualizado_em": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": f"Erro ao buscar índices: {str(e)}"
        }), 500


@bp.route("/api/correcao-monetaria", methods=["POST"])
@limiter.limit(AUTH_API_LIMIT)
@login_required
def calcular_correcao():
    """API para cálculo de correção monetária com dados reais do BCB"""
    data = request.get_json()
    
    if not data:
        return jsonify({"success": False, "message": "Dados inválidos"}), 400
    
    try:
        valor_original = Decimal(str(data.get("valor", 0)))
        data_inicial = data.get("data_inicial")
        data_final = data.get("data_final")
        indice = data.get("indice", "IPCA")
        
        if valor_original <= 0:
            return jsonify({"success": False, "message": "Valor deve ser maior que zero"}), 400
        
        if not data_inicial or not data_final:
            return jsonify({"success": False, "message": "Datas são obrigatórias"}), 400
        
        # Parse das datas
        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_final = datetime.strptime(data_final, "%Y-%m-%d")
        
        if dt_inicial >= dt_final:
            return jsonify({"success": False, "message": "Data inicial deve ser anterior à data final"}), 400
        
        # Buscar correção real do BCB
        resultado_bcb = calcular_fator_correcao(indice, dt_inicial, dt_final)
        
        if not resultado_bcb.get("sucesso"):
            return jsonify({
                "success": False, 
                "message": resultado_bcb.get("erro", "Erro ao consultar BCB")
            }), 400
        
        # Aplicar correção
        fator = Decimal(str(resultado_bcb["fator_correcao"]))
        valor_corrigido = valor_original * fator
        diferenca = valor_corrigido - valor_original
        
        return jsonify({
            "success": True,
            "resultado": {
                "valor_original": float(valor_original.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "valor_corrigido": float(valor_corrigido.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "diferenca": float(diferenca.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "percentual_correcao": resultado_bcb["percentual_correcao"],
                "meses": resultado_bcb["periodo"]["meses"],
                "indice": indice,
                "indice_nome": resultado_bcb["indice_nome"],
                "fonte": resultado_bcb["fonte"],
                "data_inicial": data_inicial,
                "data_final": data_final,
                "fator_correcao": resultado_bcb["fator_correcao"],
                "valores_mensais": resultado_bcb.get("valores_mensais", []),
                "observacao": resultado_bcb.get("observacao", "")
            }
        })
        
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
        
        if valor_principal <= 0:
            return jsonify({"success": False, "message": "Valor deve ser maior que zero"}), 400
        
        # Parse das datas
        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d").date()
        dt_final = datetime.strptime(data_final, "%Y-%m-%d").date()
        
        # Calcular dias e meses
        dias = (dt_final - dt_inicial).days
        meses = dias / 30
        
        # Taxa mensal
        if taxa_customizada:
            taxa_mensal = Decimal(str(taxa_customizada))
        else:
            taxa_mensal = TAXAS_JUROS.get(tipo_juros, {}).get("taxa", Decimal("1.0"))
        
        # Cálculo
        if capitalizado:
            # Juros compostos
            fator = (1 + taxa_mensal / 100) ** Decimal(str(meses))
            valor_com_juros = valor_principal * fator
        else:
            # Juros simples
            juros_total = valor_principal * (taxa_mensal / 100) * Decimal(str(meses))
            valor_com_juros = valor_principal + juros_total
        
        juros = valor_com_juros - valor_principal
        percentual = (juros / valor_principal) * 100
        
        return jsonify({
            "success": True,
            "resultado": {
                "valor_principal": float(valor_principal.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "valor_com_juros": float(valor_com_juros.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "juros": float(juros.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "percentual_juros": float(percentual.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "dias": dias,
                "meses": round(meses, 2),
                "taxa_mensal": float(taxa_mensal),
                "tipo_juros": tipo_juros,
                "capitalizado": capitalizado,
                "base_legal": TAXAS_JUROS.get(tipo_juros, {}).get("base_legal", "")
            }
        })
        
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
        
        resultado = {
            "valor_causa": float(valor_causa.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "tipo_honorario": tipo_honorario
        }
        
        if tipo_honorario == "contratual":
            # Honorários contratuais (percentual sobre êxito)
            honorarios = valor_causa * (percentual / 100)
            resultado["percentual"] = float(percentual)
            resultado["honorarios"] = float(honorarios.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["descricao"] = f"{percentual}% sobre o valor da causa"
            
        elif tipo_honorario == "fixo":
            # Honorários fixos
            resultado["honorarios"] = float(valor_fixo.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["descricao"] = "Valor fixo contratado"
            
        elif tipo_honorario == "sucumbencia":
            # Honorários sucumbenciais (10% a 20% conforme CPC)
            honorarios_min = valor_causa * (sucumbencia_min / 100)
            honorarios_max = valor_causa * (sucumbencia_max / 100)
            honorarios_medio = (honorarios_min + honorarios_max) / 2
            
            resultado["honorarios_min"] = float(honorarios_min.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["honorarios_max"] = float(honorarios_max.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["honorarios"] = float(honorarios_medio.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["percentual_min"] = float(sucumbencia_min)
            resultado["percentual_max"] = float(sucumbencia_max)
            resultado["descricao"] = f"Entre {sucumbencia_min}% e {sucumbencia_max}% (Art. 85, §2º, CPC)"
            resultado["base_legal"] = "Art. 85, §2º do CPC - Honorários de 10% a 20%"
            
        elif tipo_honorario == "ad_exitum":
            # Ad exitum (só recebe se ganhar)
            percentual_exitum = Decimal(str(data.get("percentual_exitum", 30)))
            honorarios = valor_causa * (percentual_exitum / 100)
            resultado["percentual"] = float(percentual_exitum)
            resultado["honorarios"] = float(honorarios.quantize(Decimal("0.01"), ROUND_HALF_UP))
            resultado["descricao"] = f"Quota litis: {percentual_exitum}% condicionado ao êxito"
            
        return jsonify({
            "success": True,
            "resultado": resultado
        })
        
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
        
        if valor_original <= 0:
            return jsonify({"success": False, "message": "Valor deve ser maior que zero"}), 400
        
        # Parse das datas
        dt_inicial = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_final = datetime.strptime(data_final, "%Y-%m-%d")
        
        dias = (dt_final - dt_inicial).days
        meses = dias / 30
        
        # 1. Correção monetária via API BCB
        resultado_bcb = calcular_fator_correcao(indice, dt_inicial, dt_final)
        
        if not resultado_bcb.get("sucesso"):
            return jsonify({
                "success": False, 
                "message": resultado_bcb.get("erro", "Erro ao consultar BCB")
            }), 400
        
        fator_correcao = Decimal(str(resultado_bcb["fator_correcao"]))
        valor_corrigido = valor_original * fator_correcao
        correcao = valor_corrigido - valor_original
        
        # 2. Juros (se aplicável e não for SELIC que já inclui)
        juros = Decimal("0")
        valor_final = valor_corrigido
        
        if aplicar_juros and indice != "SELIC":
            taxa_juros = TAXAS_JUROS.get(tipo_juros, {}).get("taxa", Decimal("1.0"))
            juros = valor_corrigido * (taxa_juros / 100) * Decimal(str(meses))
            valor_final = valor_corrigido + juros
        
        total_acrescimos = correcao + juros
        percentual_total = ((valor_final / valor_original) - 1) * 100
        
        return jsonify({
            "success": True,
            "resultado": {
                "valor_original": float(valor_original.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "correcao_monetaria": float(correcao.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "valor_corrigido": float(valor_corrigido.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "juros": float(juros.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "valor_final": float(valor_final.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "total_acrescimos": float(total_acrescimos.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "percentual_total": float(percentual_total.quantize(Decimal("0.01"), ROUND_HALF_UP)),
                "dias": dias,
                "meses": round(meses, 2),
                "indice": indice,
                "indice_nome": resultado_bcb["indice_nome"],
                "tipo_juros": tipo_juros if aplicar_juros else None,
                "data_inicial": data_inicial,
                "data_final": data_final,
                "fator_correcao": resultado_bcb["fator_correcao"],
                "fonte": resultado_bcb["fonte"],
                "observacao": "SELIC já inclui correção monetária" if indice == "SELIC" else None
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro no cálculo: {str(e)}"}), 500
