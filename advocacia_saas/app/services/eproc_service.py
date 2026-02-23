"""
Serviço de integração com tribunais via MNI/EPROC/PJe.

Substitui o DataJud. Consulta processos e andamentos via webservices SOAP
usando certificado digital A1 (.pfx) do advogado.

Suporta:
- EPROC (TRF4, TJSC, TJRS)
- PJe (maioria dos tribunais)
- e-SAJ (TJSP)
- TRT (Justiça do Trabalho)

Documentação MNI: https://www.cnj.jus.br/programas-e-acoes/mni/
"""

import hashlib
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import current_app

logger = logging.getLogger(__name__)


# =============================================================================
# ENDPOINTS DOS TRIBUNAIS
# =============================================================================

# Endpoints MNI/SOAP por tribunal
# Formato: {sigla: {sistema, wsdl_consulta, wsdl_protocolo}}
TRIBUNAL_CONFIG = {
    # --- EPROC (Justiça Federal) ---
    "TRF4": {
        "sistema": "eproc",
        "nome": "Tribunal Regional Federal da 4ª Região",
        "wsdl_consulta": "https://eproc.trf4.jus.br/eproc2trf4/controlador_ws.php?srv=intercomunicacao&wsdl",
        "wsdl_protocolo": "https://eproc.trf4.jus.br/eproc2trf4/controlador_ws.php?srv=intercomunicacao&wsdl",
    },
    "TRF1": {
        "sistema": "pje",
        "nome": "Tribunal Regional Federal da 1ª Região",
        "wsdl_consulta": "https://pje.trf1.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trf1.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRF2": {
        "sistema": "pje",
        "nome": "Tribunal Regional Federal da 2ª Região",
        "wsdl_consulta": "https://pje.trf2.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trf2.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRF3": {
        "sistema": "pje",
        "nome": "Tribunal Regional Federal da 3ª Região",
        "wsdl_consulta": "https://pje.trf3.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trf3.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRF5": {
        "sistema": "pje",
        "nome": "Tribunal Regional Federal da 5ª Região",
        "wsdl_consulta": "https://pje.trf5.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trf5.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRF6": {
        "sistema": "pje",
        "nome": "Tribunal Regional Federal da 6ª Região",
        "wsdl_consulta": "https://pje.trf6.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trf6.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    # --- EPROC (Justiça Estadual) ---
    "TJSC": {
        "sistema": "eproc",
        "nome": "Tribunal de Justiça de Santa Catarina",
        "wsdl_consulta": "https://eproc1g.tjsc.jus.br/eproc/ws/controlador_ws.php?srv=intercomunicacao&wsdl",
        "wsdl_protocolo": "https://eproc1g.tjsc.jus.br/eproc/ws/controlador_ws.php?srv=intercomunicacao&wsdl",
    },
    "TJRS": {
        "sistema": "eproc",
        "nome": "Tribunal de Justiça do Rio Grande do Sul",
        "wsdl_consulta": "https://eproc1g.tjrs.jus.br/eproc/ws/controlador_ws.php?srv=intercomunicacao&wsdl",
        "wsdl_protocolo": "https://eproc1g.tjrs.jus.br/eproc/ws/controlador_ws.php?srv=intercomunicacao&wsdl",
    },
    "TJPR": {
        "sistema": "projudi",
        "nome": "Tribunal de Justiça do Paraná",
        "wsdl_consulta": "https://projudi.tjpr.jus.br/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://projudi.tjpr.jus.br/intercomunicacao?wsdl",
    },
    # --- PJe (Justiça Estadual) ---
    "TJSP": {
        "sistema": "esaj",
        "nome": "Tribunal de Justiça de São Paulo",
        "wsdl_consulta": "https://esaj.tjsp.jus.br/cposgcr/open.do",
        "wsdl_protocolo": None,
        "api_rest": "https://esaj.tjsp.jus.br/cpopg/search.do",
    },
    "TJRJ": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça do Rio de Janeiro",
        "wsdl_consulta": "https://pje.tjrj.jus.br/1g/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjrj.jus.br/1g/intercomunicacao?wsdl",
    },
    "TJMG": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça de Minas Gerais",
        "wsdl_consulta": "https://pje.tjmg.jus.br/pje/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjmg.jus.br/pje/intercomunicacao?wsdl",
    },
    "TJBA": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça da Bahia",
        "wsdl_consulta": "https://pje.tjba.jus.br/pje/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjba.jus.br/pje/intercomunicacao?wsdl",
    },
    "TJPE": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça de Pernambuco",
        "wsdl_consulta": "https://pje.tjpe.jus.br/1g/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjpe.jus.br/1g/intercomunicacao?wsdl",
    },
    "TJCE": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça do Ceará",
        "wsdl_consulta": "https://pje.tjce.jus.br/pje1grau/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjce.jus.br/pje1grau/intercomunicacao?wsdl",
    },
    "TJGO": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça de Goiás",
        "wsdl_consulta": "https://pje.tjgo.jus.br/1g/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjgo.jus.br/1g/intercomunicacao?wsdl",
    },
    "TJDF": {
        "sistema": "pje",
        "nome": "Tribunal de Justiça do Distrito Federal",
        "wsdl_consulta": "https://pje.tjdft.jus.br/pje/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tjdft.jus.br/pje/intercomunicacao?wsdl",
    },
    # --- TRT (Justiça do Trabalho) ---
    "TRT1": {
        "sistema": "pje",
        "nome": "TRT 1ª Região - RJ",
        "wsdl_consulta": "https://pje.trt1.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt1.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT2": {
        "sistema": "pje",
        "nome": "TRT 2ª Região - SP",
        "wsdl_consulta": "https://pje.trt2.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt2.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT3": {
        "sistema": "pje",
        "nome": "TRT 3ª Região - MG",
        "wsdl_consulta": "https://pje.trt3.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt3.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT4": {
        "sistema": "pje",
        "nome": "TRT 4ª Região - RS",
        "wsdl_consulta": "https://pje.trt4.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt4.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT5": {
        "sistema": "pje",
        "nome": "TRT 5ª Região - BA",
        "wsdl_consulta": "https://pje.trt5.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt5.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT12": {
        "sistema": "pje",
        "nome": "TRT 12ª Região - SC",
        "wsdl_consulta": "https://pje.trt12.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt12.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "TRT15": {
        "sistema": "pje",
        "nome": "TRT 15ª Região - Campinas/SP",
        "wsdl_consulta": "https://pje.trt15.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.trt15.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    # --- Tribunais Superiores ---
    "TST": {
        "sistema": "pje",
        "nome": "Tribunal Superior do Trabalho",
        "wsdl_consulta": "https://pje.tst.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.tst.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
    "STJ": {
        "sistema": "pje",
        "nome": "Superior Tribunal de Justiça",
        "wsdl_consulta": "https://pje.stj.jus.br/intercomunicacao/intercomunicacao?wsdl",
        "wsdl_protocolo": "https://pje.stj.jus.br/intercomunicacao/intercomunicacao?wsdl",
    },
}

# Segmento de Justiça pelo dígito 14 do número CNJ
SEGMENTO_JUSTICA = {
    "1": "STF",
    "2": "CNJ",
    "3": "STJ",
    "4": "JF",   # Justiça Federal
    "5": "JT",   # Justiça do Trabalho
    "6": "JE",   # Justiça Eleitoral
    "7": "JM",   # Justiça Militar
    "8": "JES",  # Justiça Estadual
    "9": "JME",  # Justiça Militar Estadual
}

# Código do TRF (Justiça Federal)
CODIGO_TRF = {
    "01": "TRF1", "02": "TRF2", "03": "TRF3",
    "04": "TRF4", "05": "TRF5", "06": "TRF6",
}

# Código do Estado (Justiça Estadual)
CODIGO_ESTADO_TJ = {
    "01": "TJAC", "02": "TJAL", "03": "TJAP", "04": "TJAM",
    "05": "TJBA", "06": "TJCE", "07": "TJDF", "08": "TJES",
    "09": "TJGO", "10": "TJMA", "11": "TJMT", "12": "TJMS",
    "13": "TJMG", "14": "TJPA", "15": "TJPB", "16": "TJPR",
    "17": "TJPE", "18": "TJPI", "19": "TJRJ", "20": "TJRN",
    "21": "TJRS", "22": "TJRO", "23": "TJRR", "24": "TJSC",
    "25": "TJSP", "26": "TJSE", "27": "TJTO",
}


# =============================================================================
# UTILITÁRIOS
# =============================================================================


def sanitize_process_number(numero: str) -> str:
    """Remove formatação e retorna apenas dígitos."""
    if not numero:
        return ""
    return re.sub(r"[^\d]", "", numero)


def format_process_number(numero: str) -> str:
    """Formata número do processo no padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO"""
    digits = sanitize_process_number(numero)
    if len(digits) != 20:
        return numero
    return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:20]}"


def detect_tribunal_from_number(numero: str) -> Optional[str]:
    """
    Detecta o tribunal a partir do número do processo (formato CNJ).
    Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
    """
    numero_limpo = sanitize_process_number(numero)
    if len(numero_limpo) < 18:
        return None

    segmento = numero_limpo[13]
    codigo_tribunal = numero_limpo[14:16]

    if segmento == "4":  # Justiça Federal
        return CODIGO_TRF.get(codigo_tribunal)
    elif segmento == "8":  # Justiça Estadual
        return CODIGO_ESTADO_TJ.get(codigo_tribunal)
    elif segmento == "5":  # Justiça do Trabalho
        num = int(codigo_tribunal)
        return f"TRT{num}" if num > 0 else None
    elif segmento == "1":
        return "STF"
    elif segmento == "3":
        return "STJ"

    return None


def get_tribunal_config(tribunal_sigla: str) -> Optional[Dict]:
    """Retorna configuração do tribunal."""
    return TRIBUNAL_CONFIG.get(tribunal_sigla.upper())


def list_supported_tribunals() -> List[Dict[str, str]]:
    """Lista tribunais suportados."""
    return [
        {"sigla": k, "nome": v["nome"], "sistema": v["sistema"]}
        for k, v in sorted(TRIBUNAL_CONFIG.items())
    ]


# =============================================================================
# SERVIÇO PRINCIPAL
# =============================================================================


class EprocService:
    """
    Serviço de integração com tribunais via MNI (SOAP) e APIs alternativas.

    Métodos MNI padrão:
    - consultarProcesso: busca dados de um processo
    - consultarTeorComunicacao: ver intimações
    - entregarManifestacaoProcessual: protocolar (Fase 2)
    """

    DEFAULT_TIMEOUT = 45

    @classmethod
    def search_process(
        cls,
        numero_processo: str,
        tribunal: Optional[str] = None,
        cert_pfx_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Busca informações de um processo no tribunal via MNI/SOAP.

        Args:
            numero_processo: Número do processo (com ou sem formatação)
            tribunal: Sigla do tribunal (ex: TRF4, TJSC). Auto-detecta se não informado.
            cert_pfx_path: Caminho para o arquivo .pfx (opcional para consulta pública)
            cert_password: Senha do certificado .pfx

        Returns:
            Dict com dados do processo ou mensagem de erro.
        """
        numero_limpo = sanitize_process_number(numero_processo)

        if not numero_limpo or len(numero_limpo) < 15:
            return {
                "success": False,
                "message": "Número do processo inválido. Use o formato CNJ completo (20 dígitos).",
            }

        # Detecta tribunal se não informado
        if not tribunal:
            tribunal = detect_tribunal_from_number(numero_limpo)
            if not tribunal:
                return {
                    "success": False,
                    "message": "Não foi possível detectar o tribunal pelo número. Informe o tribunal manualmente.",
                }

        tribunal = tribunal.upper()
        config = get_tribunal_config(tribunal)

        if not config:
            return {
                "success": False,
                "message": f"Tribunal '{tribunal}' não suportado. Tribunais disponíveis: {', '.join(sorted(TRIBUNAL_CONFIG.keys()))}",
            }

        sistema = config["sistema"]
        logger.info(f"Consultando processo {numero_limpo} no {tribunal} (sistema: {sistema})")

        # Tenta via MNI/SOAP primeiro
        if config.get("wsdl_consulta"):
            result = cls._consulta_mni_soap(
                numero_limpo, tribunal, config, cert_pfx_path, cert_password
            )
            if result.get("success"):
                return result
            logger.warning(f"MNI SOAP falhou para {tribunal}: {result.get('message')}")

        # Fallback: consulta REST pública (quando disponível)
        if config.get("api_rest"):
            result = cls._consulta_rest(numero_limpo, tribunal, config)
            if result.get("success"):
                return result

        # Fallback final: scraping da consulta pública
        result = cls._consulta_publica_web(numero_limpo, tribunal, config)
        if result.get("success"):
            return result

        return {
            "success": False,
            "message": f"Não foi possível consultar o processo no {tribunal}. "
                       f"Verifique o número ou tente novamente mais tarde.",
        }

    @classmethod
    def _consulta_mni_soap(
        cls,
        numero_limpo: str,
        tribunal: str,
        config: Dict,
        cert_pfx_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta via webservice MNI (SOAP) — método padrão CNJ."""
        try:
            from zeep import Client as SoapClient
            from zeep.transports import Transport
        except ImportError:
            logger.warning("zeep não instalado. Usando fallback REST.")
            return {"success": False, "message": "Biblioteca zeep não disponível."}

        wsdl_url = config["wsdl_consulta"]

        try:
            session = requests.Session()
            session.verify = True
            session.timeout = cls.DEFAULT_TIMEOUT

            # Configurar certificado digital se fornecido
            if cert_pfx_path and cert_password:
                try:
                    from requests_pkcs12 import Pkcs12Adapter
                    session.mount("https://", Pkcs12Adapter(
                        pkcs12_filename=cert_pfx_path,
                        pkcs12_password=cert_password,
                    ))
                except ImportError:
                    # Fallback: converter .pfx para .pem
                    pem_path, key_path = cls._pfx_to_pem(cert_pfx_path, cert_password)
                    if pem_path:
                        session.cert = (pem_path, key_path)

            transport = Transport(session=session, timeout=cls.DEFAULT_TIMEOUT)
            client = SoapClient(wsdl_url, transport=transport)

            # Chamada MNI padrão: consultarProcesso
            numero_formatado = format_process_number(numero_limpo)

            response = client.service.consultarProcesso(
                idConsultante="",
                senhaConsultante="",
                numeroProcesso=numero_formatado,
                movimentos=True,
                incluirCabecalho=True,
                incluirDocumentos=False,
            )

            if response is None:
                return {"success": False, "message": "Processo não encontrado."}

            # Parsear resposta MNI
            return {
                "success": True,
                "data": cls._parse_mni_response(response, tribunal),
                "tribunal": tribunal,
                "fonte": "MNI/SOAP",
            }

        except Exception as e:
            logger.error(f"Erro MNI SOAP ({tribunal}): {e}")
            return {
                "success": False,
                "message": f"Erro na consulta SOAP: {str(e)[:200]}",
            }

    @classmethod
    def _consulta_rest(
        cls, numero_limpo: str, tribunal: str, config: Dict
    ) -> Dict[str, Any]:
        """Consulta via API REST pública (ex: e-SAJ do TJSP)."""
        api_url = config.get("api_rest")
        if not api_url:
            return {"success": False, "message": "API REST não disponível."}

        try:
            numero_formatado = format_process_number(numero_limpo)
            headers = {
                "User-Agent": "Petitio-SaaS/1.0",
                "Accept": "application/json, text/html",
            }

            # e-SAJ (TJSP) usa consulta GET com parâmetros
            if config["sistema"] == "esaj":
                params = {
                    "conversationId": "",
                    "dadosConsulta.localPesquisa.cdLocal": "-1",
                    "cbPesquisa": "NUMPROC",
                    "dadosConsulta.tipoNuProcesso": "UNIFICADO",
                    "numeroDigitoAnoUnificado": numero_formatado[:15],
                    "foroNumeroUnificado": numero_limpo[16:20],
                    "dadosConsulta.valorConsultaNuUnificado": numero_formatado,
                }
                response = requests.get(
                    api_url, params=params, headers=headers,
                    timeout=cls.DEFAULT_TIMEOUT
                )
            else:
                response = requests.get(
                    f"{api_url}?numero={numero_limpo}",
                    headers=headers,
                    timeout=cls.DEFAULT_TIMEOUT,
                )

            if response.status_code == 200:
                # Tentar parse JSON primeiro
                try:
                    data = response.json()
                    return {
                        "success": True,
                        "data": cls._parse_rest_response(data, tribunal),
                        "tribunal": tribunal,
                        "fonte": "REST",
                    }
                except ValueError:
                    # HTML — parse da consulta pública
                    return cls._parse_html_response(response.text, tribunal)

            return {
                "success": False,
                "message": f"Erro HTTP {response.status_code} na consulta REST.",
            }

        except requests.Timeout:
            return {"success": False, "message": "Timeout na consulta REST."}
        except Exception as e:
            logger.error(f"Erro REST ({tribunal}): {e}")
            return {"success": False, "message": f"Erro na consulta REST: {str(e)[:200]}"}

    @classmethod
    def _consulta_publica_web(
        cls, numero_limpo: str, tribunal: str, config: Dict
    ) -> Dict[str, Any]:
        """
        Consulta pública via web scraping como último recurso.
        Usa a página de consulta pública do tribunal.
        """
        try:
            numero_formatado = format_process_number(numero_limpo)

            # URLs de consulta pública por sistema
            consulta_urls = {
                "eproc": f"https://eproc.{tribunal.lower()}.jus.br/eproc/externo_controlador.php?acao=processo_consulta_publica",
                "pje": f"https://pje.{tribunal.lower()}.jus.br/consultapublica/ConsultaPublica/listView.seam",
                "esaj": f"https://esaj.{tribunal.lower()}.jus.br/cpopg/open.do",
            }

            sistema = config["sistema"]
            url = consulta_urls.get(sistema)

            if not url:
                return {"success": False, "message": "Sistema não suportado para consulta pública."}

            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            })

            # POST com número do processo
            if sistema == "eproc":
                response = session.post(url, data={
                    "txtNumProc": numero_formatado,
                    "selOrigem": "",
                    "chkMostrarBaixworking": "S",
                }, timeout=cls.DEFAULT_TIMEOUT)
            elif sistema == "esaj":
                response = session.get(url, params={
                    "processo.numero": numero_formatado,
                }, timeout=cls.DEFAULT_TIMEOUT)
            else:
                response = session.get(url, params={
                    "numero": numero_formatado,
                }, timeout=cls.DEFAULT_TIMEOUT)

            if response.status_code == 200 and len(response.text) > 500:
                parsed = cls._parse_html_response(response.text, tribunal)
                if parsed.get("success"):
                    parsed["fonte"] = "Consulta Pública"
                    return parsed

            return {"success": False, "message": "Processo não encontrado na consulta pública."}

        except Exception as e:
            logger.error(f"Erro consulta pública ({tribunal}): {e}")
            return {"success": False, "message": f"Erro na consulta pública: {str(e)[:200]}"}

    # =========================================================================
    # PARSERS DE RESPOSTA
    # =========================================================================

    @classmethod
    def _parse_mni_response(cls, response: Any, tribunal: str) -> Dict[str, Any]:
        """Parseia resposta do webservice MNI para formato do sistema."""
        try:
            # Estrutura padrão MNI
            processo = response if isinstance(response, dict) else {}

            # Tentar acessar como objeto zeep
            def safe_get(obj, attr, default=""):
                try:
                    val = getattr(obj, attr, None)
                    if val is not None:
                        return str(val)
                    return default
                except Exception:
                    return default

            def safe_get_nested(obj, *attrs):
                current = obj
                for attr in attrs:
                    try:
                        current = getattr(current, attr, None)
                        if current is None:
                            return ""
                    except Exception:
                        return ""
                return str(current) if current else ""

            # Extrair dados principais
            dados_basicos = getattr(response, "dadosBasicos", response)

            numero = safe_get(dados_basicos, "numero", "")
            classe_nome = safe_get_nested(dados_basicos, "classeProcessual", "nome")
            classe_codigo = safe_get_nested(dados_basicos, "classeProcessual", "codigo")
            orgao_nome = safe_get_nested(dados_basicos, "orgaoJulgador", "nomeOrgao")
            competencia = safe_get(dados_basicos, "competencia", "")
            nivel_sigilo = safe_get(dados_basicos, "nivelSigilo", "0")
            data_ajuizamento = safe_get(dados_basicos, "dataAjuizamento", "")

            # Assuntos
            assuntos = []
            assuntos_raw = getattr(dados_basicos, "assunto", []) or []
            if not isinstance(assuntos_raw, list):
                assuntos_raw = [assuntos_raw]
            for assunto in assuntos_raw:
                nome = safe_get_nested(assunto, "assuntoLocal", "descricao")
                if not nome:
                    nome = safe_get(assunto, "descricao", "")
                if nome:
                    assuntos.append(nome)

            # Partes (polo ativo/passivo)
            polo_ativo = []
            polo_passivo = []
            polos = getattr(dados_basicos, "polo", []) or []
            if not isinstance(polos, list):
                polos = [polos]
            for polo in polos:
                tipo_polo = safe_get(polo, "polo", "")
                partes = getattr(polo, "parte", []) or []
                if not isinstance(partes, list):
                    partes = [partes]
                for parte in partes:
                    nome_parte = safe_get_nested(parte, "pessoa", "nome")
                    doc_parte = safe_get_nested(parte, "pessoa", "numeroDocumentoPrincipal")
                    if tipo_polo.upper() in ("AT", "ATIVO"):
                        polo_ativo.append({"nome": nome_parte, "documento": doc_parte})
                    elif tipo_polo.upper() in ("PA", "PASSIVO"):
                        polo_passivo.append({"nome": nome_parte, "documento": doc_parte})

            # Movimentos
            movimentos = []
            movs_raw = getattr(response, "movimento", []) or []
            if not isinstance(movs_raw, list):
                movs_raw = [movs_raw]
            for mov in movs_raw[:20]:  # Últimos 20
                mov_data = safe_get(mov, "dataHora", "")
                mov_nome = safe_get_nested(mov, "movimentoLocal", "descricao")
                if not mov_nome:
                    mov_nome = safe_get(mov, "descricao", "")
                movimentos.append({
                    "data": cls._parse_date(mov_data),
                    "nome": mov_nome,
                    "codigo": safe_get(mov, "codigo", ""),
                    "tipo": safe_get(mov, "tipo", ""),
                })

            # Montar título sugerido
            autor = polo_ativo[0]["nome"] if polo_ativo else ""
            reu = polo_passivo[0]["nome"] if polo_passivo else ""
            titulo = classe_nome
            if autor and reu:
                titulo = f"{classe_nome} - {autor} vs {reu}"
            elif assuntos:
                titulo = f"{classe_nome} - {assuntos[0]}"

            # Mapear tipo de justiça
            tipo_justica = cls._map_court_type(tribunal)
            grau_mapeado = cls._detect_court_instance(tribunal, orgao_nome)

            return {
                # Campos para preencher formulário
                "process_number": format_process_number(numero) if numero else "",
                "title": titulo,
                "court": tipo_justica,
                "court_instance": grau_mapeado,
                "jurisdiction": orgao_nome,
                "distribution_date": cls._parse_date(data_ajuizamento),
                "plaintiff": autor,
                "defendant": reu,
                # Informações adicionais
                "tribunal": tribunal,
                "tribunal_nome": TRIBUNAL_CONFIG.get(tribunal, {}).get("nome", tribunal),
                "classe": classe_nome,
                "classe_codigo": classe_codigo,
                "assuntos": assuntos,
                "competencia": competencia,
                "nivel_sigilo": nivel_sigilo,
                "polo_ativo": polo_ativo,
                "polo_passivo": polo_passivo,
                "movimentos": movimentos,
                "total_movimentos": len(movimentos),
            }

        except Exception as e:
            logger.error(f"Erro ao parsear resposta MNI: {e}")
            return {
                "process_number": "",
                "title": "Erro ao processar dados do tribunal",
                "court": "",
                "court_instance": "",
                "jurisdiction": "",
                "distribution_date": None,
                "movimentos": [],
            }

    @classmethod
    def _parse_rest_response(cls, data: Dict, tribunal: str) -> Dict[str, Any]:
        """Parseia resposta de API REST."""
        # Formato varia por tribunal — tratamento genérico
        return {
            "process_number": data.get("numero", data.get("numeroProcesso", "")),
            "title": data.get("classe", {}).get("nome", data.get("assunto", "")),
            "court": cls._map_court_type(tribunal),
            "court_instance": "1ª Instância",
            "jurisdiction": data.get("orgaoJulgador", {}).get("nome", ""),
            "distribution_date": cls._parse_date(data.get("dataAjuizamento", "")),
            "plaintiff": "",
            "defendant": "",
            "tribunal": tribunal,
            "tribunal_nome": TRIBUNAL_CONFIG.get(tribunal, {}).get("nome", tribunal),
            "classe": data.get("classe", {}).get("nome", ""),
            "assuntos": [a.get("nome", "") for a in data.get("assuntos", [])],
            "movimentos": [],
            "total_movimentos": 0,
        }

    @classmethod
    def _parse_html_response(cls, html: str, tribunal: str) -> Dict[str, Any]:
        """Extrai dados de HTML de consulta pública (fallback)."""
        try:
            # Parsing básico via regex — sem dependência de BeautifulSoup
            # Extrai campos comuns das páginas de consulta pública

            def extract(pattern, text, group=1):
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                return match.group(group).strip() if match else ""

            classe = extract(r"(?:classe|tipo).*?:\s*</[^>]+>\s*([^<]+)", html)
            orgao = extract(r"(?:vara|órgão\s*julgador|juízo).*?:\s*</[^>]+>\s*([^<]+)", html)
            assunto = extract(r"assunto.*?:\s*</[^>]+>\s*([^<]+)", html)
            data_dist = extract(r"(?:distribuição|ajuização).*?:\s*</[^>]+>\s*([\d/]+)", html)
            autor = extract(r"(?:autor|requerente|reclamante).*?:\s*</[^>]+>\s*([^<]+)", html)
            reu = extract(r"(?:réu|requerido|reclamad[oa]).*?:\s*</[^>]+>\s*([^<]+)", html)

            if not classe and not orgao:
                return {"success": False, "message": "Não foi possível extrair dados da página."}

            titulo = classe
            if autor and reu:
                titulo = f"{classe} - {autor} vs {reu}"

            # Extrair movimentos
            movimentos = []
            mov_pattern = re.findall(
                r'<tr[^>]*>.*?(\d{2}/\d{2}/\d{4}).*?</td>.*?<td[^>]*>([^<]+)</td>',
                html, re.DOTALL
            )
            for data_mov, desc_mov in mov_pattern[:20]:
                movimentos.append({
                    "data": data_mov.strip(),
                    "nome": desc_mov.strip(),
                    "codigo": "",
                    "tipo": "",
                })

            return {
                "success": True,
                "data": {
                    "process_number": "",
                    "title": titulo,
                    "court": cls._map_court_type(tribunal),
                    "court_instance": "1ª Instância",
                    "jurisdiction": orgao,
                    "distribution_date": cls._parse_date_br(data_dist),
                    "plaintiff": autor,
                    "defendant": reu,
                    "tribunal": tribunal,
                    "tribunal_nome": TRIBUNAL_CONFIG.get(tribunal, {}).get("nome", tribunal),
                    "classe": classe,
                    "assuntos": [assunto] if assunto else [],
                    "movimentos": movimentos,
                    "total_movimentos": len(movimentos),
                },
            }

        except Exception as e:
            logger.error(f"Erro parse HTML ({tribunal}): {e}")
            return {"success": False, "message": "Erro ao processar consulta pública."}

    # =========================================================================
    # ANDAMENTOS / MOVIMENTAÇÕES
    # =========================================================================

    @classmethod
    def fetch_movements(
        cls,
        numero_processo: str,
        tribunal: Optional[str] = None,
        cert_pfx_path: Optional[str] = None,
        cert_password: Optional[str] = None,
        last_known_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Busca movimentações/andamentos de um processo.

        Args:
            numero_processo: Número do processo
            tribunal: Sigla do tribunal
            cert_pfx_path: Caminho para certificado .pfx
            cert_password: Senha do certificado
            last_known_date: Data da última movimentação conhecida (para buscar só novos)

        Returns:
            Dict com lista de movimentos ou mensagem de erro.
        """
        result = cls.search_process(
            numero_processo, tribunal, cert_pfx_path, cert_password
        )

        if not result.get("success"):
            return result

        data = result.get("data", {})
        movimentos = data.get("movimentos", [])

        # Filtrar apenas movimentos novos se tiver data de referência
        if last_known_date and movimentos:
            novos = []
            for mov in movimentos:
                mov_date = mov.get("data", "")
                if mov_date and mov_date > last_known_date:
                    novos.append(mov)
            movimentos = novos

        return {
            "success": True,
            "movimentos": movimentos,
            "total": len(movimentos),
            "tribunal": result.get("tribunal", tribunal),
            "fonte": result.get("fonte", ""),
        }

    # =========================================================================
    # UTILITÁRIOS INTERNOS
    # =========================================================================

    @staticmethod
    def _pfx_to_pem(pfx_path: str, password: str) -> Tuple[Optional[str], Optional[str]]:
        """Converte .pfx para .pem temporário para uso com requests."""
        try:
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                NoEncryption,
                pkcs12,
            )
            from cryptography.hazmat.primitives.serialization import (
                BestAvailableEncryption,
            )

            with open(pfx_path, "rb") as f:
                pfx_data = f.read()

            private_key, certificate, chain = pkcs12.load_key_and_certificates(
                pfx_data, password.encode()
            )

            # Salvar cert e key como PEM temporários
            cert_pem = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="wb"
            )
            key_pem = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="wb"
            )

            cert_pem.write(certificate.public_bytes(Encoding.PEM))
            if chain:
                for ca in chain:
                    cert_pem.write(ca.public_bytes(Encoding.PEM))
            cert_pem.close()

            key_pem.write(private_key.private_bytes(
                Encoding.PEM, encoding=NoEncryption()
            ))
            key_pem.close()

            return cert_pem.name, key_pem.name

        except Exception as e:
            logger.error(f"Erro ao converter PFX para PEM: {e}")
            return None, None

    @staticmethod
    def _parse_date(date_string: str) -> Optional[str]:
        """Converte data ISO ou datetime para YYYY-MM-DD."""
        if not date_string:
            return None
        try:
            date_clean = str(date_string).split("T")[0].split(" ")[0]
            # Tentar formato ISO
            dt = datetime.strptime(date_clean, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            # Tentar formato BR
            try:
                dt = datetime.strptime(date_clean, "%d/%m/%Y")
                return dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                return None

    @staticmethod
    def _parse_date_br(date_string: str) -> Optional[str]:
        """Converte data BR (dd/mm/aaaa) para YYYY-MM-DD."""
        if not date_string:
            return None
        try:
            dt = datetime.strptime(date_string.strip(), "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _map_court_type(tribunal: str) -> str:
        """Mapeia sigla do tribunal para tipo de justiça do formulário."""
        if not tribunal:
            return ""
        tribunal = tribunal.upper()
        if tribunal in ("STF",):
            return "STF"
        elif tribunal in ("STJ",):
            return "STJ"
        elif tribunal in ("TST",):
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

    @staticmethod
    def _detect_court_instance(tribunal: str, orgao_nome: str) -> str:
        """Detecta a instância pela sigla do tribunal e nome do órgão."""
        if not tribunal:
            return "1ª Instância"
        tribunal = tribunal.upper()
        orgao_lower = (orgao_nome or "").lower()

        # Tribunais superiores
        if tribunal in ("STF", "STJ", "TST"):
            return "Instância Superior"

        # Se o nome do órgão contém pista
        if "turma recursal" in orgao_lower or "câmara" in orgao_lower:
            return "2ª Instância"
        if "vara" in orgao_lower or "juizado" in orgao_lower:
            return "1ª Instância"

        return "1ª Instância"
