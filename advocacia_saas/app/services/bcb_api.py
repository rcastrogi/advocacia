"""
Serviço para consulta de índices econômicos via API do Banco Central do Brasil.

API Documentação: https://dadosabertos.bcb.gov.br/

Códigos das Séries SGS:
- 433: IPCA (mensal)
- 188: INPC (mensal)
- 189: IGP-M (mensal)
- 226: TR (mensal)
- 11: SELIC (diária)
- 4390: CDI (diária)
"""

import logging
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Códigos das séries no Sistema Gerenciador de Séries (SGS) do BCB
SERIES_BCB = {
    "IPCA": {
        "codigo": 433,
        "nome": "IPCA - Índice de Preços ao Consumidor Amplo",
        "fonte": "IBGE",
        "periodicidade": "mensal",
        "uso": "Correção monetária geral, débitos judiciais",
    },
    "INPC": {
        "codigo": 188,
        "nome": "INPC - Índice Nacional de Preços ao Consumidor",
        "fonte": "IBGE",
        "periodicidade": "mensal",
        "uso": "Correção trabalhista e previdenciária",
    },
    "IGPM": {
        "codigo": 189,
        "nome": "IGP-M - Índice Geral de Preços do Mercado",
        "fonte": "FGV",
        "periodicidade": "mensal",
        "uso": "Contratos de aluguel, reajustes contratuais",
    },
    "TR": {
        "codigo": 226,
        "nome": "TR - Taxa Referencial",
        "fonte": "Banco Central",
        "periodicidade": "mensal",
        "uso": "FGTS, poupança, financiamentos",
    },
    "SELIC": {
        "codigo": 4390,  # SELIC acumulada no mês
        "nome": "Taxa SELIC",
        "fonte": "Banco Central",
        "periodicidade": "mensal",
        "uso": "Débitos fazendários (EC 113/2021)",
    },
}

# URL base da API do BCB
BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


def buscar_serie_bcb(codigo: int, data_inicio: str, data_fim: str) -> Optional[list]:
    """
    Busca série temporal da API do BCB.

    Args:
        codigo: Código da série SGS
        data_inicio: Data inicial (formato DD/MM/YYYY)
        data_fim: Data final (formato DD/MM/YYYY)

    Returns:
        Lista de dicts com data e valor, ou None em caso de erro
    """
    try:
        url = BCB_API_URL.format(codigo=codigo)
        params = {"formato": "json", "dataInicial": data_inicio, "dataFinal": data_fim}

        # Timeout curto para não travar a interface
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        dados = response.json()
        logger.info(f"BCB API: Série {codigo} retornou {len(dados)} registros")
        return dados

    except requests.Timeout:
        logger.warning(f"Timeout ao buscar série {codigo} do BCB")
        return None
    except requests.RequestException as e:
        logger.error(f"Erro ao buscar série {codigo} do BCB: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao processar série {codigo}: {e}")
        return None


# Taxas mensais aproximadas (fallback quando API não responde)
TAXAS_FALLBACK = {
    "IPCA": Decimal("0.40"),
    "INPC": Decimal("0.45"),
    "IGPM": Decimal("0.50"),
    "TR": Decimal("0.10"),
    "SELIC": Decimal("0.85"),
}


def calcular_fator_correcao(
    indice: str, data_inicial: datetime, data_final: datetime
) -> Dict[str, Any]:
    """
    Calcula o fator de correção monetária para um período usando dados reais do BCB.
    Se a API não responder, usa valores aproximados como fallback.

    Args:
        indice: Nome do índice (IPCA, INPC, IGPM, TR, SELIC)
        data_inicial: Data inicial do período
        data_final: Data final do período

    Returns:
        Dict com fator, percentual e detalhes do cálculo
    """
    if indice not in SERIES_BCB:
        return {
            "sucesso": False,
            "erro": f"Índice '{indice}' não suportado",
            "indices_disponiveis": list(SERIES_BCB.keys()),
        }

    serie_info = SERIES_BCB[indice]
    codigo = serie_info["codigo"]

    # Calcular meses entre as datas (para fallback)
    dias = (data_final - data_inicial).days
    meses = max(1, dias / 30)

    # Formatar datas para API (DD/MM/YYYY)
    dt_inicio_str = data_inicial.strftime("%d/%m/%Y")
    dt_fim_str = data_final.strftime("%d/%m/%Y")

    # Buscar dados do BCB
    dados = buscar_serie_bcb(codigo, dt_inicio_str, dt_fim_str)

    # Se API falhou, usar fallback
    if not dados or len(dados) == 0:
        logger.warning(f"API BCB não respondeu para {indice}, usando fallback")
        return _calcular_fallback(indice, serie_info, meses)

    # Calcular fator acumulado (índices mensais são variações percentuais)
    fator_acumulado = Decimal("1")
    valores_usados = []

    for item in dados:
        try:
            # Valor vem como string com vírgula como separador decimal
            valor_str = item.get("valor", "0").replace(",", ".")
            valor = Decimal(valor_str)

            # Converter percentual para fator (ex: 0.5% -> 1.005)
            fator_mensal = 1 + (valor / 100)
            fator_acumulado *= fator_mensal

            valores_usados.append(
                {
                    "data": item.get("data"),
                    "valor": float(valor),
                    "fator": float(fator_mensal),
                }
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Valor inválido ignorado: {item}")
            continue

    # Calcular percentual de correção
    percentual_correcao = (fator_acumulado - 1) * 100

    return {
        "sucesso": True,
        "indice": indice,
        "indice_nome": serie_info["nome"],
        "fonte": serie_info["fonte"],
        "fator_correcao": float(
            fator_acumulado.quantize(Decimal("0.000001"), ROUND_HALF_UP)
        ),
        "percentual_correcao": float(
            percentual_correcao.quantize(Decimal("0.01"), ROUND_HALF_UP)
        ),
        "periodo": {
            "inicio": data_inicial.strftime("%d/%m/%Y"),
            "fim": data_final.strftime("%d/%m/%Y"),
            "meses": len(valores_usados),
        },
        "valores_mensais": valores_usados[-12:]
        if len(valores_usados) > 12
        else valores_usados,  # Últimos 12 meses
        "observacao": f"Dados oficiais do {serie_info['fonte']} via API do Banco Central do Brasil",
    }


def _calcular_fallback(indice: str, serie_info: dict, meses: float) -> Dict[str, Any]:
    """
    Calcula correção usando taxas aproximadas quando API BCB não responde.
    """
    taxa_mensal = TAXAS_FALLBACK.get(indice, Decimal("0.40"))
    fator = (1 + taxa_mensal / 100) ** Decimal(str(meses))
    percentual = (fator - 1) * 100

    return {
        "sucesso": True,
        "indice": indice,
        "indice_nome": serie_info["nome"],
        "fonte": serie_info["fonte"] + " (estimativa)",
        "fator_correcao": float(fator.quantize(Decimal("0.000001"), ROUND_HALF_UP)),
        "percentual_correcao": float(
            percentual.quantize(Decimal("0.01"), ROUND_HALF_UP)
        ),
        "periodo": {"inicio": "", "fim": "", "meses": int(meses)},
        "valores_mensais": [],
        "observacao": f"⚠️ Valores aproximados (taxa média de {taxa_mensal}% a.m.). API do BCB indisponível.",
    }


@lru_cache(maxsize=100)
def obter_ultimo_indice(indice: str) -> Optional[Dict[str, Any]]:
    """
    Obtém o valor mais recente de um índice (com cache).

    Args:
        indice: Nome do índice

    Returns:
        Dict com último valor disponível ou None
    """
    if indice not in SERIES_BCB:
        return None

    codigo = SERIES_BCB[indice]["codigo"]

    # Buscar últimos 3 meses para garantir que pegamos o mais recente
    hoje = datetime.now()
    inicio = hoje - timedelta(days=90)

    dados = buscar_serie_bcb(
        codigo, inicio.strftime("%d/%m/%Y"), hoje.strftime("%d/%m/%Y")
    )

    if not dados or len(dados) == 0:
        return None

    # Pegar o mais recente
    ultimo = dados[-1]

    try:
        valor = float(ultimo.get("valor", "0").replace(",", "."))
    except (ValueError, TypeError):
        valor = 0.0

    return {
        "indice": indice,
        "data": ultimo.get("data"),
        "valor": valor,
        "fonte": SERIES_BCB[indice]["fonte"],
    }


def obter_indices_atuais() -> Dict[str, Any]:
    """
    Obtém os valores mais recentes de todos os índices.
    Retorna taxa_mensal para uso no cálculo local JavaScript.

    Returns:
        Dict com todos os índices e seus últimos valores
    """
    resultado = {}

    for indice in SERIES_BCB.keys():
        info = SERIES_BCB[indice].copy()
        ultimo = obter_ultimo_indice(indice)

        if ultimo:
            info["ultimo_valor"] = ultimo["valor"]
            info["ultima_data"] = ultimo["data"]
            info["taxa_mensal"] = ultimo["valor"]  # A API retorna variação percentual
            info["fonte"] = "BCB"
            info["status"] = "disponivel"
        else:
            # Usar fallback
            fallback = float(TAXAS_FALLBACK.get(indice, Decimal("0.40")))
            info["ultimo_valor"] = fallback
            info["ultima_data"] = None
            info["taxa_mensal"] = fallback
            info["fonte"] = "Estimativa"
            info["status"] = "fallback"

        resultado[indice] = info

    return resultado
