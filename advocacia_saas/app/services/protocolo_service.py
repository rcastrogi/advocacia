"""
Serviço de Peticionamento Eletrônico via MNI/EPROC.

Implementa o método `entregarManifestacaoProcessual` do padrão MNI (CNJ)
para protocolar petições diretamente nos sistemas dos tribunais.

Fluxo:
1. Validar documentos (formato, tamanho)
2. Assinar PDFs com certificado A1
3. Codificar documentos em base64
4. Montar envelope MNI (SOAP)
5. Enviar via webservice
6. Processar resposta (número do protocolo)

Documentação MNI: https://www.cnj.jus.br/programas-e-acoes/mni/
Especificação: entregarManifestacaoProcessual (2.2)
"""

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# Tipos de documento MNI padrão
TIPO_DOCUMENTO_MNI = {
    "peticao_inicial": {"codigo": 60, "descricao": "Petição Inicial"},
    "contestacao": {"codigo": 61, "descricao": "Contestação"},
    "recurso": {"codigo": 62, "descricao": "Recurso"},
    "agravo": {"codigo": 63, "descricao": "Agravo"},
    "embargos": {"codigo": 64, "descricao": "Embargos"},
    "peticao_simples": {"codigo": 2, "descricao": "Petição"},
    "peticao_diversa": {"codigo": 7, "descricao": "Petição Diversa"},
    "procuracao": {"codigo": 37, "descricao": "Procuração"},
    "substabelecimento": {"codigo": 38, "descricao": "Substabelecimento"},
    "comprovante": {"codigo": 52, "descricao": "Comprovante de Pagamento"},
    "documento": {"codigo": 999, "descricao": "Documento"},
    "ata_audiencia": {"codigo": 70, "descricao": "Ata de Audiência"},
    "laudo_pericial": {"codigo": 71, "descricao": "Laudo Pericial"},
    "certidao": {"codigo": 72, "descricao": "Certidão"},
    "declaracao": {"codigo": 73, "descricao": "Declaração"},
    "contrato": {"codigo": 74, "descricao": "Contrato"},
    "outros": {"codigo": 999, "descricao": "Outros Documentos"},
}

# Classes processuais frequentes (para pré-seleção)
CLASSES_PROCESSUAIS = {
    "acao_alimentos": {"codigo": 8826, "nome": "Ação de Alimentos"},
    "acao_divorcio": {"codigo": 8827, "nome": "Ação de Divórcio"},
    "acao_cobranca": {"codigo": 159, "nome": "Ação de Cobrança"},
    "exec_titulo_extrajudicial": {"codigo": 156, "nome": "Execução de Título Extrajudicial"},
    "acao_indenizacao": {"codigo": 12120, "nome": "Ação de Indenização"},
    "mandado_seguranca": {"codigo": 120, "nome": "Mandado de Segurança"},
    "habeas_corpus": {"codigo": 307, "nome": "Habeas Corpus"},
    "acao_trabalhista": {"codigo": 985, "nome": "Reclamação Trabalhista"},
    "recurso_ordinario": {"codigo": 993, "nome": "Recurso Ordinário"},
    "agravo_instrumento": {"codigo": 202, "nome": "Agravo de Instrumento"},
    "apelacao": {"codigo": 197, "nome": "Apelação"},
    "embargos_declaracao": {"codigo": 48, "nome": "Embargos de Declaração"},
    "cumprimento_sentenca": {"codigo": 156, "nome": "Cumprimento de Sentença"},
    "juizado_especial": {"codigo": 436, "nome": "Procedimento do Juizado Especial"},
}


class ProtocoloService:
    """
    Peticionamento eletrônico via MNI (Modelo Nacional de Interoperabilidade).
    Protocola petições e documentos diretamente nos tribunais.
    """

    DEFAULT_TIMEOUT = 60  # Protocolo pode demorar mais que consulta
    MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB por documento
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total por protocolo

    @classmethod
    def protocolar(
        cls,
        numero_processo: str,
        tribunal: str,
        documentos: List[Dict[str, Any]],
        tipo_documento: str,
        cert_pfx_path: str,
        cert_password: str,
        dados_complementares: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Protocola documentos em processo existente.

        Args:
            numero_processo: Número CNJ do processo.
            tribunal: Sigla do tribunal (ex: TRF4, TJSC).
            documentos: Lista de dicts com {'nome', 'bytes', 'mime_type'}.
            tipo_documento: Chave do tipo (ex: 'peticao_simples').
            cert_pfx_path: Caminho do .pfx temporário.
            cert_password: Senha do certificado.
            dados_complementares: Dict com dados extras (descrição, urgência, etc).

        Returns:
            Dict com resultado: success, protocolo, mensagem, etc.
        """
        from app.services.eproc_service import (
            format_process_number,
            get_tribunal_config,
            sanitize_process_number,
        )

        # Validações
        numero_limpo = sanitize_process_number(numero_processo)
        if not numero_limpo or len(numero_limpo) < 15:
            return {"success": False, "message": "Número do processo inválido."}

        config = get_tribunal_config(tribunal.upper())
        if not config:
            return {
                "success": False,
                "message": f"Tribunal '{tribunal}' não suportado para protocolo.",
            }

        wsdl_protocolo = config.get("wsdl_protocolo")
        if not wsdl_protocolo:
            return {
                "success": False,
                "message": f"Tribunal '{tribunal}' não suporta protocolo eletrônico via MNI.",
            }

        if not cert_pfx_path or not cert_password:
            return {
                "success": False,
                "message": "Certificado digital (A1) é obrigatório para protocolar.",
            }

        # Validar documentos
        validation = cls._validar_documentos(documentos)
        if not validation["valid"]:
            return {"success": False, "message": validation["message"]}

        # Assinar documentos
        docs_assinados = cls._assinar_documentos(
            documentos, cert_pfx_path, cert_password
        )
        if not docs_assinados["success"]:
            return docs_assinados

        # Tipo de documento MNI
        tipo_mni = TIPO_DOCUMENTO_MNI.get(tipo_documento, TIPO_DOCUMENTO_MNI["outros"])

        # Montar e enviar
        numero_formatado = format_process_number(numero_limpo)
        dados = dados_complementares or {}

        logger.info(
            f"Protocolando {len(documentos)} documento(s) no processo "
            f"{numero_formatado} ({tribunal})"
        )

        # Enviar via MNI SOAP
        result = cls._enviar_mni(
            numero_formatado=numero_formatado,
            tribunal=tribunal,
            config=config,
            documentos_assinados=docs_assinados["documentos"],
            tipo_mni=tipo_mni,
            cert_pfx_path=cert_pfx_path,
            cert_password=cert_password,
            dados=dados,
        )

        return result

    @classmethod
    def protocolar_novo_processo(
        cls,
        tribunal: str,
        classe_processual: str,
        documentos: List[Dict[str, Any]],
        partes: Dict[str, List[Dict]],
        cert_pfx_path: str,
        cert_password: str,
        dados_complementares: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Protocola uma petição inicial (processo novo) via MNI.

        Args:
            tribunal: Sigla do tribunal.
            classe_processual: Chave da classe (ex: 'acao_cobranca') ou código.
            documentos: Lista de documentos.
            partes: {"polo_ativo": [...], "polo_passivo": [...]}.
            cert_pfx_path: Caminho do .pfx.
            cert_password: Senha do certificado.
            dados_complementares: Dados extras.

        Returns:
            Dict com resultado incluindo número do processo atribuído.
        """
        from app.services.eproc_service import get_tribunal_config

        config = get_tribunal_config(tribunal.upper())
        if not config:
            return {"success": False, "message": f"Tribunal '{tribunal}' não suportado."}

        wsdl_protocolo = config.get("wsdl_protocolo")
        if not wsdl_protocolo:
            return {
                "success": False,
                "message": f"Protocolo eletrônico não disponível para {tribunal}.",
            }

        if not cert_pfx_path or not cert_password:
            return {
                "success": False,
                "message": "Certificado digital obrigatório.",
            }

        # Validar documentos
        validation = cls._validar_documentos(documentos)
        if not validation["valid"]:
            return {"success": False, "message": validation["message"]}

        # Assinar documentos
        docs_assinados = cls._assinar_documentos(
            documentos, cert_pfx_path, cert_password
        )
        if not docs_assinados["success"]:
            return docs_assinados

        # Resolver classe processual
        if classe_processual in CLASSES_PROCESSUAIS:
            classe_info = CLASSES_PROCESSUAIS[classe_processual]
        else:
            try:
                classe_info = {"codigo": int(classe_processual), "nome": ""}
            except (ValueError, TypeError):
                return {"success": False, "message": "Classe processual inválida."}

        logger.info(
            f"Protocolando novo processo no {tribunal} - "
            f"Classe: {classe_info.get('nome', classe_info['codigo'])}"
        )

        result = cls._enviar_novo_processo_mni(
            tribunal=tribunal,
            config=config,
            classe_info=classe_info,
            documentos_assinados=docs_assinados["documentos"],
            partes=partes,
            cert_pfx_path=cert_pfx_path,
            cert_password=cert_password,
            dados=dados_complementares or {},
        )

        return result

    # =========================================================================
    # VALIDAÇÕES
    # =========================================================================

    @classmethod
    def _validar_documentos(cls, documentos: List[Dict]) -> Dict[str, Any]:
        """Valida documentos antes do envio."""
        if not documentos:
            return {"valid": False, "message": "Nenhum documento fornecido."}

        total_size = 0
        mimes_aceitos = [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/tiff",
            "text/html",
        ]

        for i, doc in enumerate(documentos):
            doc_bytes = doc.get("bytes", b"")
            mime = doc.get("mime_type", "application/pdf")
            nome = doc.get("nome", f"documento_{i+1}")

            if not doc_bytes:
                return {"valid": False, "message": f"Documento '{nome}' está vazio."}

            if len(doc_bytes) > cls.MAX_DOC_SIZE:
                size_mb = len(doc_bytes) / (1024 * 1024)
                return {
                    "valid": False,
                    "message": f"Documento '{nome}' excede 10MB ({size_mb:.1f}MB).",
                }

            if mime not in mimes_aceitos:
                return {
                    "valid": False,
                    "message": f"Tipo '{mime}' não aceito para '{nome}'. Use PDF, JPEG, PNG ou TIFF.",
                }

            total_size += len(doc_bytes)

        if total_size > cls.MAX_TOTAL_SIZE:
            total_mb = total_size / (1024 * 1024)
            return {
                "valid": False,
                "message": f"Tamanho total ({total_mb:.1f}MB) excede o limite de 50MB.",
            }

        return {"valid": True, "message": f"{len(documentos)} documento(s) válido(s)."}

    # =========================================================================
    # ASSINATURA DE DOCUMENTOS
    # =========================================================================

    @classmethod
    def _assinar_documentos(
        cls,
        documentos: List[Dict],
        cert_pfx_path: str,
        cert_password: str,
    ) -> Dict[str, Any]:
        """Assina todos os PDFs com o certificado A1."""
        from app.services.pdf_signer import PdfSigner

        docs_assinados = []

        for doc in documentos:
            doc_bytes = doc["bytes"]
            nome = doc.get("nome", "documento.pdf")
            mime = doc.get("mime_type", "application/pdf")

            # Só assina PDFs
            if mime == "application/pdf":
                signed_bytes, error = PdfSigner.sign_pdf(
                    doc_bytes, cert_pfx_path, cert_password,
                    reason=f"Peticionamento - {nome}",
                )
                if error:
                    logger.warning(
                        f"Falha ao assinar '{nome}': {error}. Enviando sem assinatura."
                    )
                    signed_bytes = doc_bytes
            else:
                signed_bytes = doc_bytes

            # Gerar hash para verificação
            doc_hash = hashlib.sha256(signed_bytes).hexdigest()

            docs_assinados.append({
                "nome": nome,
                "bytes": signed_bytes,
                "base64": base64.b64encode(signed_bytes).decode(),
                "mime_type": mime,
                "hash_sha256": doc_hash,
                "tamanho": len(signed_bytes),
            })

        return {"success": True, "documentos": docs_assinados}

    # =========================================================================
    # ENVIO MNI (SOAP)
    # =========================================================================

    @classmethod
    def _enviar_mni(
        cls,
        numero_formatado: str,
        tribunal: str,
        config: Dict,
        documentos_assinados: List[Dict],
        tipo_mni: Dict,
        cert_pfx_path: str,
        cert_password: str,
        dados: Dict,
    ) -> Dict[str, Any]:
        """
        Envia manifestação processual via webservice MNI.
        Usa o método SOAP entregarManifestacaoProcessual.
        """
        try:
            from zeep import Client as SoapClient
            from zeep.transports import Transport
        except ImportError:
            return {
                "success": False,
                "message": "Biblioteca zeep não disponível para protocolo SOAP.",
            }

        wsdl_url = config["wsdl_protocolo"]

        try:
            session = requests.Session()
            session.verify = True
            session.timeout = cls.DEFAULT_TIMEOUT

            # Configurar certificado digital (obrigatório para protocolo)
            try:
                from requests_pkcs12 import Pkcs12Adapter
                session.mount("https://", Pkcs12Adapter(
                    pkcs12_filename=cert_pfx_path,
                    pkcs12_password=cert_password,
                ))
            except ImportError:
                # Fallback: converter .pfx para .pem
                from app.services.eproc_service import EprocService
                pem_path, key_path = EprocService._pfx_to_pem(cert_pfx_path, cert_password)
                if pem_path:
                    session.cert = (pem_path, key_path)
                else:
                    return {
                        "success": False,
                        "message": "Erro ao configurar certificado para protocolo.",
                    }

            transport = Transport(session=session, timeout=cls.DEFAULT_TIMEOUT)
            client = SoapClient(wsdl_url, transport=transport)

            # Montar array de documentos MNI
            docs_mni = []
            for doc in documentos_assinados:
                doc_mni = {
                    "tipoDocumento": tipo_mni["codigo"],
                    "descricao": dados.get("descricao", tipo_mni["descricao"]),
                    "nomeArquivo": doc["nome"],
                    "mimeType": doc["mime_type"],
                    "conteudo": doc["base64"],
                    "hash": doc["hash_sha256"],
                    "nivelSigilo": dados.get("sigilo", 0),
                }
                docs_mni.append(doc_mni)

            # Chamar entregarManifestacaoProcessual
            response = client.service.entregarManifestacaoProcessual(
                idManifestante="",
                senhaManifestante="",
                numeroProcesso=numero_formatado,
                documento=docs_mni,
                dataEnvio=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            )

            # Processar resposta
            return cls._parse_protocolo_response(response, tribunal)

        except Exception as e:
            logger.error(f"Erro no protocolo MNI ({tribunal}): {e}")
            return {
                "success": False,
                "message": f"Erro ao protocolar no {tribunal}: {str(e)[:200]}",
            }

    @classmethod
    def _enviar_novo_processo_mni(
        cls,
        tribunal: str,
        config: Dict,
        classe_info: Dict,
        documentos_assinados: List[Dict],
        partes: Dict,
        cert_pfx_path: str,
        cert_password: str,
        dados: Dict,
    ) -> Dict[str, Any]:
        """
        Envia petição inicial (processo novo) via MNI.
        Usa entregarManifestacaoProcessual com parâmetros de processo novo.
        """
        try:
            from zeep import Client as SoapClient
            from zeep.transports import Transport
        except ImportError:
            return {"success": False, "message": "Biblioteca zeep não disponível."}

        wsdl_url = config["wsdl_protocolo"]

        try:
            session = requests.Session()
            session.verify = True
            session.timeout = cls.DEFAULT_TIMEOUT

            try:
                from requests_pkcs12 import Pkcs12Adapter
                session.mount("https://", Pkcs12Adapter(
                    pkcs12_filename=cert_pfx_path,
                    pkcs12_password=cert_password,
                ))
            except ImportError:
                from app.services.eproc_service import EprocService
                pem_path, key_path = EprocService._pfx_to_pem(cert_pfx_path, cert_password)
                if pem_path:
                    session.cert = (pem_path, key_path)
                else:
                    return {"success": False, "message": "Erro ao configurar certificado."}

            transport = Transport(session=session, timeout=cls.DEFAULT_TIMEOUT)
            client = SoapClient(wsdl_url, transport=transport)

            # Montar documentos
            docs_mni = []
            tipo_mni = TIPO_DOCUMENTO_MNI.get("peticao_inicial", TIPO_DOCUMENTO_MNI["peticao_simples"])
            for doc in documentos_assinados:
                docs_mni.append({
                    "tipoDocumento": tipo_mni["codigo"],
                    "descricao": doc.get("descricao", tipo_mni["descricao"]),
                    "nomeArquivo": doc["nome"],
                    "mimeType": doc["mime_type"],
                    "conteudo": doc["base64"],
                    "hash": doc["hash_sha256"],
                    "nivelSigilo": dados.get("sigilo", 0),
                })

            # Montar partes (polo ativo e passivo)
            polos_mni = []
            for polo_tipo, polo_partes in [
                ("AT", partes.get("polo_ativo", [])),
                ("PA", partes.get("polo_passivo", [])),
            ]:
                for parte in polo_partes:
                    polos_mni.append({
                        "polo": polo_tipo,
                        "parte": {
                            "pessoa": {
                                "nome": parte.get("nome", ""),
                                "numeroDocumentoPrincipal": parte.get("documento", ""),
                                "tipoPessoa": parte.get("tipo", "fisica"),
                            }
                        }
                    })

            # Enviar processo novo
            response = client.service.entregarManifestacaoProcessual(
                idManifestante="",
                senhaManifestante="",
                numeroProcesso="",  # Vazio = processo novo
                classeProcessual=classe_info["codigo"],
                polo=polos_mni,
                documento=docs_mni,
                dataEnvio=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            )

            result = cls._parse_protocolo_response(response, tribunal)

            if result.get("success"):
                result["novo_processo"] = True

            return result

        except Exception as e:
            logger.error(f"Erro protocolo novo processo ({tribunal}): {e}")
            return {
                "success": False,
                "message": f"Erro ao protocolar novo processo: {str(e)[:200]}",
            }

    # =========================================================================
    # PARSE RESPOSTA
    # =========================================================================

    @classmethod
    def _parse_protocolo_response(cls, response: Any, tribunal: str) -> Dict[str, Any]:
        """Parseia resposta do webservice de protocolo."""
        try:
            def safe_get(obj, attr, default=""):
                try:
                    val = getattr(obj, attr, None)
                    return str(val) if val is not None else default
                except Exception:
                    return default

            sucesso = safe_get(response, "sucesso", "false")
            mensagem = safe_get(response, "mensagem", "")
            protocolo = safe_get(response, "protocoloRecebimento", "")
            data_recebimento = safe_get(response, "dataRecebimento", "")
            numero_processo = safe_get(response, "numeroProcesso", "")

            # Alguns tribunais retornam em campos diferentes
            if not protocolo:
                protocolo = safe_get(response, "recibo", "")
            if not protocolo:
                protocolo = safe_get(response, "codigoRecebimento", "")

            is_success = sucesso.lower() in ("true", "1", "sim", "s")

            if is_success:
                logger.info(
                    f"Protocolo registrado: {protocolo} no {tribunal} - "
                    f"Processo: {numero_processo}"
                )
                return {
                    "success": True,
                    "message": "Petição protocolada com sucesso!",
                    "protocolo": protocolo,
                    "data_protocolo": data_recebimento,
                    "numero_processo": numero_processo,
                    "tribunal": tribunal,
                }
            else:
                logger.warning(f"Protocolo rejeitado ({tribunal}): {mensagem}")
                return {
                    "success": False,
                    "message": mensagem or "Protocolo rejeitado pelo tribunal.",
                    "tribunal": tribunal,
                }

        except Exception as e:
            logger.error(f"Erro ao parsear resposta de protocolo: {e}")
            return {
                "success": False,
                "message": f"Erro ao processar resposta: {str(e)[:200]}",
            }

    # =========================================================================
    # UTILITÁRIOS
    # =========================================================================

    @classmethod
    def get_tipos_documento(cls) -> List[Dict[str, Any]]:
        """Retorna lista de tipos de documento disponíveis."""
        return [
            {"chave": k, "codigo": v["codigo"], "descricao": v["descricao"]}
            for k, v in TIPO_DOCUMENTO_MNI.items()
        ]

    @classmethod
    def get_classes_processuais(cls) -> List[Dict[str, Any]]:
        """Retorna lista de classes processuais disponíveis."""
        return [
            {"chave": k, "codigo": v["codigo"], "nome": v["nome"]}
            for k, v in CLASSES_PROCESSUAIS.items()
        ]

    @classmethod
    def verificar_tribunal_suporta_protocolo(cls, tribunal: str) -> Dict[str, Any]:
        """Verifica se o tribunal suporta protocolo eletrônico."""
        from app.services.eproc_service import get_tribunal_config

        config = get_tribunal_config(tribunal.upper())
        if not config:
            return {
                "suporta": False,
                "message": f"Tribunal '{tribunal}' não encontrado.",
            }

        wsdl = config.get("wsdl_protocolo")
        return {
            "suporta": bool(wsdl),
            "tribunal": tribunal.upper(),
            "sistema": config.get("sistema", ""),
            "nome": config.get("nome", tribunal),
            "message": "Protocolo eletrônico disponível" if wsdl else "Protocolo eletrônico não disponível para este tribunal.",
        }
