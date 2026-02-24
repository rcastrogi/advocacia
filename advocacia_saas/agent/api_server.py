"""
Servidor HTTP local do Petitio Assinador.

Roda em localhost:7777 e expõe API REST para o Petitio web
se comunicar com o smart card do advogado.

Segurança:
- Aceita apenas conexões de localhost
- CORS restrito a petitio.onrender.com e localhost
- PIN solicitado a cada operação de assinatura
- Nenhuma chave privada é transmitida
"""

import base64
import hashlib
import json
import logging
import threading
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from smartcard_service import SmartCardService

logger = logging.getLogger(__name__)

# Domínios permitidos via CORS
ALLOWED_ORIGINS = [
    "https://petitio.onrender.com",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:3000",
]

# Porta do agente local
AGENT_PORT = 7777
AGENT_VERSION = "1.0.0"

# Instância global do serviço de smart card
smartcard = SmartCardService()


def create_agent_app() -> Flask:
    """Cria e configura a aplicação Flask do agente."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "petitio-agent-local-only"

    # CORS restrito
    CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=False)

    # ================================================================
    # ENDPOINTS
    # ================================================================

    @app.route("/status", methods=["GET"])
    def status():
        """
        Verifica se o agente está rodando e retorna info do smart card.
        O Petitio web chama isso para saber se o agente está disponível.
        """
        sc_status = smartcard.get_status()

        return jsonify({
            "online": True,
            "version": AGENT_VERSION,
            "app": "Petitio Assinador",
            "smartcard": sc_status,
        })

    @app.route("/certificados", methods=["GET"])
    def listar_certificados():
        """
        Lista certificados no smart card (sem PIN — só dados públicos).
        """
        certs = smartcard.listar_certificados()

        # Remover bytes DER da resposta JSON
        certs_clean = []
        for c in certs:
            cert_copy = {k: v for k, v in c.items() if k != "_der_bytes"}
            certs_clean.append(cert_copy)

        return jsonify({
            "success": True,
            "certificados": certs_clean,
            "total": len(certs_clean),
        })

    @app.route("/certificados/detalhe", methods=["POST"])
    def detalhe_certificado():
        """
        Retorna detalhes do certificado (requer PIN para acessar dados privados).
        """
        data = request.get_json() or {}
        pin = data.get("pin", "").strip()

        if not pin:
            return jsonify({"success": False, "message": "PIN é obrigatório."}), 400

        certs = smartcard.listar_certificados(pin)
        if not certs:
            return jsonify({
                "success": False,
                "message": "Nenhum certificado encontrado ou PIN incorreto.",
            })

        certs_clean = []
        for c in certs:
            cert_copy = {k: v for k, v in c.items() if k != "_der_bytes"}
            certs_clean.append(cert_copy)

        return jsonify({
            "success": True,
            "certificados": certs_clean,
        })

    @app.route("/assinar", methods=["POST"])
    def assinar_documento():
        """
        Assina um documento (PDF em base64) com o certificado A3.

        Body JSON:
            - documento_b64: PDF em base64
            - pin: PIN do cartão
            - slot_id: (opcional) ID do slot do leitor
            - cert_id_hex: (opcional) ID do certificado específico
            - reason: (opcional) Motivo da assinatura
        """
        data = request.get_json() or {}

        documento_b64 = data.get("documento_b64", "")
        pin = data.get("pin", "").strip()
        slot_id = data.get("slot_id", 0)
        cert_id_hex = data.get("cert_id_hex")
        reason = data.get("reason", "Peticionamento Eletrônico")

        if not documento_b64:
            return jsonify({"success": False, "message": "Documento não fornecido."}), 400
        if not pin:
            return jsonify({"success": False, "message": "PIN é obrigatório."}), 400

        try:
            pdf_bytes = base64.b64decode(documento_b64)
        except Exception:
            return jsonify({"success": False, "message": "Documento base64 inválido."}), 400

        # Validar tamanho (máx 50MB)
        if len(pdf_bytes) > 50 * 1024 * 1024:
            return jsonify({
                "success": False,
                "message": "Documento muito grande (máximo 50MB).",
            }), 400

        # Assinar no smart card
        sig_bytes, error = smartcard.assinar_pdf(
            pdf_bytes, pin, slot_id, cert_id_hex, reason
        )

        if error:
            return jsonify({"success": False, "message": error})

        # Retornar assinatura em base64
        sig_b64 = base64.b64encode(sig_bytes).decode()
        doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

        return jsonify({
            "success": True,
            "assinatura_b64": sig_b64,
            "algoritmo": "SHA256withRSA",
            "documento_hash_sha256": doc_hash,
            "message": "Documento assinado com sucesso!",
        })

    @app.route("/consultar", methods=["POST"])
    def consultar_processo():
        """
        Consulta processo no tribunal usando certificado A3 para mTLS.

        Body JSON:
            - numero_processo: Número do processo
            - tribunal: Sigla do tribunal (ex: TJSE)
            - pin: PIN do cartão
            - slot_id: (opcional) ID do slot
            - cert_id_hex: (opcional) ID do certificado
        """
        data = request.get_json() or {}

        numero_processo = data.get("numero_processo", "").strip()
        tribunal = data.get("tribunal", "").strip()
        pin = data.get("pin", "").strip()
        slot_id = data.get("slot_id", 0)
        cert_id_hex = data.get("cert_id_hex")

        if not numero_processo:
            return jsonify({"success": False, "message": "Número do processo obrigatório."}), 400
        if not pin:
            return jsonify({"success": False, "message": "PIN é obrigatório."}), 400

        # Para consulta com A3, precisamos exportar o certificado público
        # e usar a chave privada para o handshake TLS via PKCS#11
        # Isso é mais complexo — requer custom TLS adapter
        try:
            import PyKCS11
            import ssl
            import tempfile

            pkcs11 = smartcard._get_lib()
            slots = pkcs11.getSlotList(tokenPresent=True)
            if not slots:
                return jsonify({"success": False, "message": "Cartão não encontrado."})

            actual_slot = slots[min(slot_id, len(slots) - 1)]

            # Abrir sessão e obter certificado
            session = pkcs11.openSession(actual_slot, PyKCS11.CKF_SERIAL_SESSION)
            session.login(pin)

            # Extrair certificado público (DER)
            certs = session.findObjects([
                (PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)
            ])

            if not certs:
                session.logout()
                session.closeSession()
                return jsonify({"success": False, "message": "Certificado não encontrado no cartão."})

            cert_obj = certs[0]
            attrs = session.getAttributeValue(cert_obj, [PyKCS11.CKA_VALUE])
            cert_der = bytes(attrs[0])

            session.logout()
            session.closeSession()

            # Converter DER para PEM para usar com requests
            from cryptography import x509
            from cryptography.hazmat.primitives.serialization import Encoding

            cert = x509.load_der_x509_certificate(cert_der)
            cert_pem = cert.public_bytes(Encoding.PEM)

            # Salvar PEM temporário
            cert_tmp = tempfile.NamedTemporaryFile(
                suffix=".pem", delete=False, mode="wb"
            )
            cert_tmp.write(cert_pem)
            cert_tmp.close()

            # Nota: Para mTLS completo com A3, precisaríamos de um
            # custom TLS adapter que usa PKCS#11 para o handshake.
            # Por ora, fazemos consulta pública + assinatura no cartão.

            # Importar EprocService e fazer consulta pública
            # (sem certificado no servidor — a consulta mTLS real
            # requereria um engine PKCS#11 para OpenSSL)
            return jsonify({
                "success": False,
                "message": (
                    "Consulta com A3 via navegador ainda não suportada para mTLS. "
                    "Use a consulta padrão do Petitio (funciona para tribunais com "
                    "acesso público) ou cadastre um certificado A1 para consultas automáticas."
                ),
                "certificado_info": {
                    "nome": cert.subject.get_attributes_for_oid(
                        x509.oid.NameOID.COMMON_NAME
                    )[0].value if cert.subject.get_attributes_for_oid(
                        x509.oid.NameOID.COMMON_NAME
                    ) else "Desconhecido",
                },
            })

        except Exception as e:
            logger.error(f"Erro na consulta com A3: {e}")
            return jsonify({
                "success": False,
                "message": f"Erro ao acessar cartão: {str(e)[:200]}",
            })

    @app.route("/ping", methods=["GET"])
    def ping():
        """Health check simples."""
        return jsonify({"pong": True, "version": AGENT_VERSION})

    # ================================================================
    # MIDDLEWARE
    # ================================================================

    @app.before_request
    def check_origin():
        """Bloqueia requisições que não sejam de origens permitidas."""
        origin = request.headers.get("Origin", "")
        referer = request.headers.get("Referer", "")

        # Permitir requisições sem Origin (chamadas diretas/curl)
        if not origin and not referer:
            return

        # Verificar se a origem é permitida
        allowed = False
        for allowed_origin in ALLOWED_ORIGINS:
            if origin.startswith(allowed_origin) or referer.startswith(allowed_origin):
                allowed = True
                break

        if not allowed:
            return jsonify({"error": "Origin not allowed"}), 403

    @app.errorhandler(Exception)
    def handle_error(e):
        logger.error(f"Erro não tratado: {e}")
        return jsonify({
            "success": False,
            "message": f"Erro interno: {str(e)[:200]}",
        }), 500

    return app


def run_server(port: int = AGENT_PORT):
    """Inicia o servidor Flask em background."""
    app = create_agent_app()

    # Roda em thread separada para não bloquear a UI do tray
    server_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            use_reloader=False,
            threaded=True,
        ),
        daemon=True,
    )
    server_thread.start()
    logger.info(f"Petitio Assinador rodando em http://127.0.0.1:{port}")
    return server_thread


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_agent_app()
    app.run(host="127.0.0.1", port=AGENT_PORT, debug=True)
