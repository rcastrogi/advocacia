"""
Serviços da Calculadora Jurídica
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

from app.services.bcb_api import calcular_fator_correcao, obter_indices_atuais

# Taxas de juros legais (fixas por lei)
TAXAS_JUROS = {
    "mora_civil": {
        "nome": "Juros Moratórios - Código Civil",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "Art. 406, CC c/c Art. 161, §1º, CTN",
    },
    "mora_trabalhista": {
        "nome": "Juros Moratórios - Trabalhista",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "Art. 39, §1º, Lei 8.177/91",
    },
    "selic": {
        "nome": "Taxa SELIC (via API BCB)",
        "taxa": Decimal("1.0"),
        "periodo": "mensal",
        "base_legal": "EC 113/2021 - Fazenda Pública",
    },
}


@dataclass
class CalculoResultado:
    """Resultado de um cálculo."""

    sucesso: bool
    resultado: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None


class IndicesService:
    """Serviço para índices do BCB."""

    @staticmethod
    def obter_indices() -> Dict[str, Any]:
        """Obtém índices atualizados do BCB."""
        return obter_indices_atuais()

    @staticmethod
    def get_taxas_juros() -> Dict[str, Any]:
        """Retorna taxas de juros legais."""
        return TAXAS_JUROS


class CorrecaoMonetariaService:
    """Serviço para cálculo de correção monetária."""

    @staticmethod
    def calcular(
        valor: Decimal,
        data_inicial: datetime,
        data_final: datetime,
        indice: str = "IPCA",
    ) -> CalculoResultado:
        """Calcula correção monetária com dados reais do BCB."""
        if valor <= 0:
            return CalculoResultado(sucesso=False, erro="Valor deve ser maior que zero")

        if data_inicial >= data_final:
            return CalculoResultado(
                sucesso=False, erro="Data inicial deve ser anterior à data final"
            )

        # Buscar correção real do BCB
        resultado_bcb = calcular_fator_correcao(indice, data_inicial, data_final)

        if not resultado_bcb.get("sucesso"):
            return CalculoResultado(
                sucesso=False,
                erro=resultado_bcb.get("erro", "Erro ao consultar BCB"),
            )

        # Aplicar correção
        fator = Decimal(str(resultado_bcb["fator_correcao"]))
        valor_corrigido = valor * fator
        diferenca = valor_corrigido - valor

        resultado = {
            "valor_original": float(valor.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "valor_corrigido": float(
                valor_corrigido.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "diferenca": float(diferenca.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "percentual_correcao": resultado_bcb["percentual_correcao"],
            "meses": resultado_bcb["periodo"]["meses"],
            "indice": indice,
            "indice_nome": resultado_bcb["indice_nome"],
            "fonte": resultado_bcb["fonte"],
            "data_inicial": data_inicial.strftime("%Y-%m-%d"),
            "data_final": data_final.strftime("%Y-%m-%d"),
            "fator_correcao": resultado_bcb["fator_correcao"],
            "valores_mensais": resultado_bcb.get("valores_mensais", []),
            "observacao": resultado_bcb.get("observacao", ""),
        }

        return CalculoResultado(sucesso=True, resultado=resultado)


class JurosService:
    """Serviço para cálculo de juros."""

    @staticmethod
    def calcular(
        valor_principal: Decimal,
        data_inicial: datetime,
        data_final: datetime,
        tipo_juros: str = "mora_civil",
        taxa_customizada: Optional[Decimal] = None,
        capitalizado: bool = False,
    ) -> CalculoResultado:
        """Calcula juros simples ou compostos."""
        if valor_principal <= 0:
            return CalculoResultado(sucesso=False, erro="Valor deve ser maior que zero")

        # Calcular dias e meses
        dias = (data_final - data_inicial).days
        meses = dias / 30

        # Taxa mensal
        if taxa_customizada:
            taxa_mensal = taxa_customizada
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

        resultado = {
            "valor_principal": float(
                valor_principal.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "valor_com_juros": float(
                valor_com_juros.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "juros": float(juros.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "percentual_juros": float(
                percentual.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "dias": dias,
            "meses": round(meses, 2),
            "taxa_mensal": float(taxa_mensal),
            "tipo_juros": tipo_juros,
            "capitalizado": capitalizado,
            "base_legal": TAXAS_JUROS.get(tipo_juros, {}).get("base_legal", ""),
        }

        return CalculoResultado(sucesso=True, resultado=resultado)


class HonorariosService:
    """Serviço para cálculo de honorários advocatícios."""

    @staticmethod
    def calcular(
        valor_causa: Decimal,
        tipo_honorario: str = "contratual",
        percentual: Decimal = Decimal("20"),
        valor_fixo: Decimal = Decimal("0"),
        sucumbencia_min: Decimal = Decimal("10"),
        sucumbencia_max: Decimal = Decimal("20"),
        percentual_exitum: Decimal = Decimal("30"),
    ) -> CalculoResultado:
        """Calcula honorários advocatícios."""
        resultado = {
            "valor_causa": float(valor_causa.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "tipo_honorario": tipo_honorario,
        }

        if tipo_honorario == "contratual":
            honorarios = valor_causa * (percentual / 100)
            resultado["percentual"] = float(percentual)
            resultado["honorarios"] = float(
                honorarios.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["descricao"] = f"{percentual}% sobre o valor da causa"

        elif tipo_honorario == "fixo":
            resultado["honorarios"] = float(
                valor_fixo.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["descricao"] = "Valor fixo contratado"

        elif tipo_honorario == "sucumbencia":
            honorarios_min = valor_causa * (sucumbencia_min / 100)
            honorarios_max = valor_causa * (sucumbencia_max / 100)
            honorarios_medio = (honorarios_min + honorarios_max) / 2

            resultado["honorarios_min"] = float(
                honorarios_min.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["honorarios_max"] = float(
                honorarios_max.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["honorarios"] = float(
                honorarios_medio.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["percentual_min"] = float(sucumbencia_min)
            resultado["percentual_max"] = float(sucumbencia_max)
            resultado["descricao"] = (
                f"Entre {sucumbencia_min}% e {sucumbencia_max}% (Art. 85, §2º, CPC)"
            )
            resultado["base_legal"] = "Art. 85, §2º do CPC - Honorários de 10% a 20%"

        elif tipo_honorario == "ad_exitum":
            honorarios = valor_causa * (percentual_exitum / 100)
            resultado["percentual"] = float(percentual_exitum)
            resultado["honorarios"] = float(
                honorarios.quantize(Decimal("0.01"), ROUND_HALF_UP)
            )
            resultado["descricao"] = (
                f"Quota litis: {percentual_exitum}% condicionado ao êxito"
            )

        return CalculoResultado(sucesso=True, resultado=resultado)


class CalculoCompletoService:
    """Serviço para cálculo completo (correção + juros)."""

    @staticmethod
    def calcular(
        valor_original: Decimal,
        data_inicial: datetime,
        data_final: datetime,
        indice: str = "IPCA",
        tipo_juros: str = "mora_civil",
        aplicar_juros: bool = True,
    ) -> CalculoResultado:
        """Calcula correção monetária e juros combinados."""
        if valor_original <= 0:
            return CalculoResultado(sucesso=False, erro="Valor deve ser maior que zero")

        dias = (data_final - data_inicial).days
        meses = dias / 30

        # 1. Correção monetária via API BCB
        resultado_bcb = calcular_fator_correcao(indice, data_inicial, data_final)

        if not resultado_bcb.get("sucesso"):
            return CalculoResultado(
                sucesso=False,
                erro=resultado_bcb.get("erro", "Erro ao consultar BCB"),
            )

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

        resultado = {
            "valor_original": float(
                valor_original.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "correcao_monetaria": float(
                correcao.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "valor_corrigido": float(
                valor_corrigido.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "juros": float(juros.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "valor_final": float(
                valor_final.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "total_acrescimos": float(
                total_acrescimos.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "percentual_total": float(
                percentual_total.quantize(Decimal("0.01"), ROUND_HALF_UP)
            ),
            "dias": dias,
            "meses": round(meses, 2),
            "indice": indice,
            "indice_nome": resultado_bcb["indice_nome"],
            "tipo_juros": tipo_juros if aplicar_juros else None,
            "data_inicial": data_inicial.strftime("%Y-%m-%d"),
            "data_final": data_final.strftime("%Y-%m-%d"),
            "fator_correcao": resultado_bcb["fator_correcao"],
            "fonte": resultado_bcb["fonte"],
            "observacao": "SELIC já inclui correção monetária"
            if indice == "SELIC"
            else None,
        }

        return CalculoResultado(sucesso=True, resultado=resultado)
