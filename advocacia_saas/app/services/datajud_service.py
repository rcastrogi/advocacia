"""
Serviço de integração com a API DataJud do CNJ.

Permite consultar informações públicas de processos judiciais.
Documentação: https://datajud-wiki.cnj.jus.br/
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Mapeamento de tribunais para endpoints da API
TRIBUNAL_ENDPOINTS = {
    # Tribunais Superiores
    "STF": "api_publica_stf",
    "STJ": "api_publica_stj",
    "TST": "api_publica_tst",
    "TSE": "api_publica_tse",
    "STM": "api_publica_stm",
    # Tribunais Regionais Federais
    "TRF1": "api_publica_trf1",
    "TRF2": "api_publica_trf2",
    "TRF3": "api_publica_trf3",
    "TRF4": "api_publica_trf4",
    "TRF5": "api_publica_trf5",
    "TRF6": "api_publica_trf6",
    # Tribunais de Justiça Estaduais
    "TJAC": "api_publica_tjac",
    "TJAL": "api_publica_tjal",
    "TJAM": "api_publica_tjam",
    "TJAP": "api_publica_tjap",
    "TJBA": "api_publica_tjba",
    "TJCE": "api_publica_tjce",
    "TJDF": "api_publica_tjdf",
    "TJES": "api_publica_tjes",
    "TJGO": "api_publica_tjgo",
    "TJMA": "api_publica_tjma",
    "TJMG": "api_publica_tjmg",
    "TJMS": "api_publica_tjms",
    "TJMT": "api_publica_tjmt",
    "TJPA": "api_publica_tjpa",
    "TJPB": "api_publica_tjpb",
    "TJPE": "api_publica_tjpe",
    "TJPI": "api_publica_tjpi",
    "TJPR": "api_publica_tjpr",
    "TJRJ": "api_publica_tjrj",
    "TJRN": "api_publica_tjrn",
    "TJRO": "api_publica_tjro",
    "TJRR": "api_publica_tjrr",
    "TJRS": "api_publica_tjrs",
    "TJSC": "api_publica_tjsc",
    "TJSE": "api_publica_tjse",
    "TJSP": "api_publica_tjsp",
    "TJTO": "api_publica_tjto",
    # Tribunais Regionais do Trabalho
    "TRT1": "api_publica_trt1",
    "TRT2": "api_publica_trt2",
    "TRT3": "api_publica_trt3",
    "TRT4": "api_publica_trt4",
    "TRT5": "api_publica_trt5",
    "TRT6": "api_publica_trt6",
    "TRT7": "api_publica_trt7",
    "TRT8": "api_publica_trt8",
    "TRT9": "api_publica_trt9",
    "TRT10": "api_publica_trt10",
    "TRT11": "api_publica_trt11",
    "TRT12": "api_publica_trt12",
    "TRT13": "api_publica_trt13",
    "TRT14": "api_publica_trt14",
    "TRT15": "api_publica_trt15",
    "TRT16": "api_publica_trt16",
    "TRT17": "api_publica_trt17",
    "TRT18": "api_publica_trt18",
    "TRT19": "api_publica_trt19",
    "TRT20": "api_publica_trt20",
    "TRT21": "api_publica_trt21",
    "TRT22": "api_publica_trt22",
    "TRT23": "api_publica_trt23",
    "TRT24": "api_publica_trt24",
}

# Código do segmento de justiça no número do processo (dígito 14)
SEGMENTO_JUSTICA = {
    "1": "STF",  # Supremo Tribunal Federal
    "2": "CNJ",  # Conselho Nacional de Justiça
    "3": "STJ",  # Superior Tribunal de Justiça
    "4": "JF",  # Justiça Federal
    "5": "JT",  # Justiça do Trabalho
    "6": "JE",  # Justiça Eleitoral
    "7": "JM",  # Justiça Militar da União
    "8": "JE",  # Justiça dos Estados e do DF
    "9": "JME",  # Justiça Militar Estadual
}

# Código do TRF no número do processo (dígitos 16-17 para Justiça Federal)
CODIGO_TRF = {
    "01": "TRF1",
    "02": "TRF2",
    "03": "TRF3",
    "04": "TRF4",
    "05": "TRF5",
    "06": "TRF6",
}

# Código do Estado no número do processo (dígitos 16-17 para Justiça Estadual)
CODIGO_ESTADO = {
    "01": "TJAC",
    "02": "TJAL",
    "03": "TJAP",
    "04": "TJAM",
    "05": "TJBA",
    "06": "TJCE",
    "07": "TJDF",
    "08": "TJES",
    "09": "TJGO",
    "10": "TJMA",
    "11": "TJMT",
    "12": "TJMS",
    "13": "TJMG",
    "14": "TJPA",
    "15": "TJPB",
    "16": "TJPR",
    "17": "TJPE",
    "18": "TJPI",
    "19": "TJRJ",
    "20": "TJRN",
    "21": "TJRS",
    "22": "TJRO",
    "23": "TJRR",
    "24": "TJSC",
    "25": "TJSP",
    "26": "TJSE",
    "27": "TJTO",
}


def sanitize_process_number(numero: str) -> str:
    """Remove formatação e retorna apenas dígitos."""
    if not numero:
        return ""
    return re.sub(r"[^\d]", "", numero)


def detect_tribunal_from_number(numero: str) -> Optional[str]:
    """
    Detecta o tribunal a partir do número do processo.

    Formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    - NNNNNNN: Número sequencial (7 dígitos)
    - DD: Dígito verificador (2 dígitos)
    - AAAA: Ano do ajuizamento (4 dígitos)
    - J: Segmento de Justiça (1 dígito)
    - TR: Código do Tribunal (2 dígitos)
    - OOOO: Código da Origem (4 dígitos)
    """
    numero_limpo = sanitize_process_number(numero)

    if len(numero_limpo) < 18:
        return None

    # Dígito 14 (posição 13): Segmento de Justiça
    segmento = numero_limpo[13]

    # Dígitos 15-16 (posições 14-15): Código do Tribunal
    codigo_tribunal = numero_limpo[14:16]

    if segmento == "4":  # Justiça Federal
        return CODIGO_TRF.get(codigo_tribunal)
    elif segmento == "8":  # Justiça Estadual
        return CODIGO_ESTADO.get(codigo_tribunal)
    elif segmento == "5":  # Justiça do Trabalho
        return f"TRT{int(codigo_tribunal)}"
    elif segmento == "1":
        return "STF"
    elif segmento == "3":
        return "STJ"

    return None


class DataJudService:
    """Serviço para consultas à API pública do DataJud."""

    BASE_URL = "https://api-publica.datajud.cnj.jus.br"
    DEFAULT_TIMEOUT = 30

    @classmethod
    def get_api_key(cls) -> str:
        """Obtém a API Key configurada."""
        return current_app.config.get(
            "DATAJUD_API_KEY",
            "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==",
        )

    @classmethod
    def search_process(
        cls, numero_processo: str, tribunal: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca informações de um processo no DataJud.

        Args:
            numero_processo: Número do processo (com ou sem formatação)
            tribunal: Sigla do tribunal (ex: TRF1, TJSP). Se não informado,
                     tenta detectar pelo número.

        Returns:
            Dict com os dados do processo ou mensagem de erro.
        """
        numero_limpo = sanitize_process_number(numero_processo)

        if not numero_limpo or len(numero_limpo) < 15:
            return {
                "success": False,
                "message": "Número do processo inválido. Use o formato CNJ completo.",
            }

        # Detecta tribunal se não informado
        if not tribunal:
            tribunal = detect_tribunal_from_number(numero_limpo)
            if not tribunal:
                return {
                    "success": False,
                    "message": "Não foi possível detectar o tribunal. Verifique o número do processo.",
                }

        # Obtém endpoint do tribunal
        endpoint = TRIBUNAL_ENDPOINTS.get(tribunal.upper())
        if not endpoint:
            return {
                "success": False,
                "message": f"Tribunal '{tribunal}' não suportado pela API DataJud.",
            }

        # Monta requisição
        url = f"{cls.BASE_URL}/{endpoint}/_search"
        headers = {
            "Authorization": f"ApiKey {cls.get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {"query": {"match": {"numeroProcesso": numero_limpo}}}

        try:
            logger.info(f"Consultando DataJud: {tribunal} - {numero_limpo}")

            response = requests.post(
                url, headers=headers, json=payload, timeout=cls.DEFAULT_TIMEOUT
            )

            if response.status_code == 401:
                logger.error("DataJud: API Key inválida")
                return {
                    "success": False,
                    "message": "Falha na autenticação com a API DataJud.",
                }

            if response.status_code != 200:
                logger.error(f"DataJud error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Erro na consulta ao DataJud (HTTP {response.status_code}).",
                }

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            if not hits:
                return {
                    "success": False,
                    "message": "Processo não encontrado no DataJud.",
                }

            # Extrai dados do primeiro resultado
            processo = hits[0].get("_source", {})

            return {
                "success": True,
                "data": cls._parse_process_data(processo),
                "raw": processo,  # Dados brutos para debug
            }

        except requests.Timeout:
            logger.error("DataJud: Timeout na requisição")
            return {
                "success": False,
                "message": "Tempo limite excedido. Tente novamente.",
            }
        except requests.RequestException as e:
            logger.error(f"DataJud request error: {e}")
            return {"success": False, "message": "Erro de conexão com a API DataJud."}
        except Exception as e:
            logger.exception(f"DataJud unexpected error: {e}")
            return {"success": False, "message": "Erro inesperado na consulta."}

    @classmethod
    def _parse_process_data(cls, processo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforma os dados do DataJud para o formato do sistema.

        Mapeia campos do DataJud para campos do formulário de processo.
        """
        # Extrai classe processual (tipo de ação)
        classe = processo.get("classe", {})
        classe_nome = classe.get("nome", "")

        # Extrai órgão julgador
        orgao = processo.get("orgaoJulgador", {})
        orgao_nome = orgao.get("nome", "")

        # Extrai assuntos
        assuntos = processo.get("assuntos", [])
        assuntos_nomes = [a.get("nome", "") for a in assuntos if a.get("nome")]

        # Extrai tribunal
        tribunal = processo.get("tribunal", "")

        # Extrai grau
        grau = processo.get("grau", "")
        grau_mapeado = cls._map_court_instance(grau)

        # Extrai data de ajuizamento
        data_ajuizamento = processo.get("dataAjuizamento", "")
        data_ajuizamento_formatada = cls._parse_date(data_ajuizamento)

        # Extrai movimentos (últimos 5)
        movimentos = processo.get("movimentos", [])
        ultimos_movimentos = []
        for mov in movimentos[:5]:
            ultimos_movimentos.append(
                {
                    "codigo": mov.get("codigo"),
                    "nome": mov.get("nome", ""),
                    "data": cls._parse_date(mov.get("dataHora", "")),
                }
            )

        # Monta título sugerido
        titulo_sugerido = classe_nome
        if assuntos_nomes:
            titulo_sugerido = f"{classe_nome} - {assuntos_nomes[0]}"

        # Mapeia tipo de justiça
        tipo_justica = cls._map_court_type(tribunal)

        return {
            # Campos para preencher o formulário
            "process_number": processo.get("numeroProcesso", ""),
            "title": titulo_sugerido,
            "court": tipo_justica,
            "court_instance": grau_mapeado,
            "jurisdiction": orgao_nome,
            "distribution_date": data_ajuizamento_formatada,
            # Informações adicionais para exibição
            "tribunal": tribunal,
            "grau": grau,
            "classe": classe_nome,
            "classe_codigo": classe.get("codigo"),
            "assuntos": assuntos_nomes,
            "formato": processo.get("formato", {}).get("nome", ""),
            "sistema": processo.get("sistema", {}).get("nome", ""),
            "nivel_sigilo": processo.get("nivelSigilo", 0),
            "ultima_atualizacao": cls._parse_date(
                processo.get("dataHoraUltimaAtualizacao", "")
            ),
            "movimentos": ultimos_movimentos,
        }

    @staticmethod
    def _parse_date(date_string: str) -> Optional[str]:
        """Converte data ISO para formato YYYY-MM-DD."""
        if not date_string:
            return None
        try:
            # Remove timezone e parse
            date_clean = date_string.split("T")[0]
            dt = datetime.strptime(date_clean, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _map_court_instance(grau: str) -> str:
        """Mapeia grau do DataJud para instância do sistema."""
        grau_map = {
            "G1": "1ª Instância",
            "G2": "2ª Instância",
            "SUP": "Instância Superior",
            "JE": "1ª Instância",  # Juizado Especial
            "TR": "2ª Instância",  # Turma Recursal
        }
        return grau_map.get(grau, "1ª Instância")

    @staticmethod
    def _map_court_type(tribunal: str) -> str:
        """Mapeia sigla do tribunal para tipo de justiça."""
        if not tribunal:
            return ""

        tribunal = tribunal.upper()

        if tribunal == "STF":
            return "STF"
        elif tribunal == "STJ":
            return "STJ"
        elif tribunal == "TST":
            return "Justiça do Trabalho"
        elif tribunal.startswith("TRF"):
            return "Justiça Federal"
        elif tribunal.startswith("TRT"):
            return "Justiça do Trabalho"
        elif tribunal.startswith("TJ"):
            return "Justiça Estadual"
        elif tribunal.startswith("TRE"):
            return "Justiça Eleitoral"

        return "Outro"

    @classmethod
    def search_multiple_tribunals(
        cls, numero_processo: str, tribunais: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Busca em múltiplos tribunais se não encontrar no detectado.

        Útil quando o número do processo está incompleto ou com erro.
        """
        numero_limpo = sanitize_process_number(numero_processo)

        if not numero_limpo:
            return {"success": False, "message": "Número do processo não informado."}

        # Tenta detectar o tribunal primeiro
        tribunal_detectado = detect_tribunal_from_number(numero_limpo)

        if tribunal_detectado:
            result = cls.search_process(numero_limpo, tribunal_detectado)
            if result.get("success"):
                return result

        # Se não encontrou, tenta nos tribunais mais comuns
        tribunais_tentativa = tribunais or ["TJSP", "TJRJ", "TJMG", "TRF1", "TRF3"]

        for tribunal in tribunais_tentativa:
            if tribunal == tribunal_detectado:
                continue

            result = cls.search_process(numero_limpo, tribunal)
            if result.get("success"):
                return result

        return {
            "success": False,
            "message": "Processo não encontrado nos tribunais consultados.",
        }
