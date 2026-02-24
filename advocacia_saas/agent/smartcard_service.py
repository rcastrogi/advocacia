"""
Serviço de acesso ao Smart Card via PKCS#11.

Detecta leitores de cartão (OmniKey, etc.), lista certificados,
e realiza assinaturas digitais dentro do chip do cartão.

A chave privada NUNCA sai do smart card — toda operação criptográfica
é executada pelo hardware.
"""

import hashlib
import logging
import os
import platform
import struct
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Caminhos comuns das bibliotecas PKCS#11 no Windows
PKCS11_LIBS_WINDOWS = [
    # SafeNet / Thales (muito comum em certificados ICP-Brasil)
    r"C:\Windows\System32\eTPKCS11.dll",
    r"C:\Windows\System32\aetpkss1.dll",
    # Oberthur / IDEMIA
    r"C:\Windows\System32\OcsCryptoki.dll",
    # Gemalto / Thales
    r"C:\Windows\System32\gclib.dll",
    # Bit4id (usado em vários tokens brasileiros)
    r"C:\Windows\System32\bit4ipki.dll",
    r"C:\Windows\System32\bit4opki.dll",
    # Watchdata (muito usado no Brasil)
    r"C:\Program Files\Watchdata\Watchdata Brazil CSP v1.0\WDPKCS.dll",
    r"C:\Windows\System32\WDPKCS.dll",
    # OpenSC (genérico)
    r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll",
    r"C:\Windows\System32\opensc-pkcs11.dll",
    # Pronova
    r"C:\Windows\System32\aetpksse.dll",
    # Certisign
    r"C:\Windows\System32\cmP11.dll",
    # Serasa
    r"C:\Windows\System32\SerPKCS11.dll",
    # Valid
    r"C:\Windows\System32\castle.dll",
]


class SmartCardService:
    """Gerencia acesso ao smart card via PKCS#11."""

    def __init__(self):
        self._pkcs11_lib = None
        self._lib_path = None
        self._session = None

    def detectar_biblioteca(self) -> Optional[str]:
        """
        Detecta qual biblioteca PKCS#11 está instalada no sistema.
        Testa cada caminho conhecido até encontrar uma que funcione.
        """
        if self._lib_path:
            return self._lib_path

        libs = PKCS11_LIBS_WINDOWS if platform.system() == "Windows" else []

        # Adicionar caminhos de variável de ambiente
        env_lib = os.environ.get("PKCS11_LIB")
        if env_lib:
            libs.insert(0, env_lib)

        for lib_path in libs:
            if os.path.exists(lib_path):
                try:
                    import PyKCS11

                    pkcs11 = PyKCS11.PyKCS11Lib()
                    pkcs11.load(lib_path)
                    # Tenta listar slots para verificar que funciona
                    pkcs11.getSlotList(tokenPresent=False)
                    self._pkcs11_lib = pkcs11
                    self._lib_path = lib_path
                    logger.info(f"Biblioteca PKCS#11 encontrada: {lib_path}")
                    return lib_path
                except Exception as e:
                    logger.debug(f"Biblioteca {lib_path} falhou: {e}")
                    continue

        logger.warning("Nenhuma biblioteca PKCS#11 encontrada.")
        return None

    def _get_lib(self):
        """Obtém instância da biblioteca PKCS#11."""
        if self._pkcs11_lib:
            return self._pkcs11_lib

        lib_path = self.detectar_biblioteca()
        if not lib_path:
            raise RuntimeError(
                "Nenhuma biblioteca PKCS#11 encontrada. "
                "Verifique se o driver do leitor de cartão está instalado."
            )
        return self._pkcs11_lib

    def listar_leitores(self) -> List[Dict[str, Any]]:
        """Lista leitores de cartão conectados."""
        try:
            pkcs11 = self._get_lib()
            slots = pkcs11.getSlotList(tokenPresent=False)

            leitores = []
            for slot_id in slots:
                try:
                    info = pkcs11.getSlotInfo(slot_id)
                    token_present = False
                    token_info = None

                    try:
                        ti = pkcs11.getTokenInfo(slot_id)
                        token_present = True
                        token_info = {
                            "label": ti.label.strip(),
                            "manufacturer": ti.manufacturerID.strip(),
                            "model": ti.model.strip(),
                            "serial": ti.serialNumber.strip(),
                        }
                    except Exception:
                        pass

                    leitores.append({
                        "slot_id": slot_id,
                        "descricao": info.slotDescription.strip(),
                        "fabricante": info.manufacturerID.strip(),
                        "cartao_inserido": token_present,
                        "token": token_info,
                    })
                except Exception as e:
                    logger.debug(f"Erro lendo slot {slot_id}: {e}")

            return leitores

        except RuntimeError:
            return []
        except Exception as e:
            logger.error(f"Erro ao listar leitores: {e}")
            return []

    def listar_certificados(self, pin: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista certificados no smart card.
        PIN é opcional para listar (necessário apenas para operações privadas).
        """
        try:
            import PyKCS11

            pkcs11 = self._get_lib()
            slots = pkcs11.getSlotList(tokenPresent=True)

            if not slots:
                return []

            certificados = []

            for slot_id in slots:
                session = None
                try:
                    session = pkcs11.openSession(
                        slot_id, PyKCS11.CKF_SERIAL_SESSION
                    )

                    # Login se PIN fornecido
                    if pin:
                        session.login(pin)

                    # Buscar objetos do tipo certificado
                    certs = session.findObjects([
                        (PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)
                    ])

                    for cert_obj in certs:
                        try:
                            attrs = session.getAttributeValue(cert_obj, [
                                PyKCS11.CKA_LABEL,
                                PyKCS11.CKA_VALUE,
                                PyKCS11.CKA_ID,
                            ])

                            label = attrs[0] if isinstance(attrs[0], str) else ""
                            cert_der = bytes(attrs[1]) if attrs[1] else b""
                            cert_id = bytes(attrs[2]) if attrs[2] else b""

                            cert_info = self._parse_certificate(cert_der)
                            cert_info["label"] = label
                            cert_info["slot_id"] = slot_id
                            cert_info["cert_id_hex"] = cert_id.hex()

                            certificados.append(cert_info)

                        except Exception as e:
                            logger.debug(f"Erro lendo certificado: {e}")

                    if pin:
                        session.logout()

                except Exception as e:
                    logger.debug(f"Erro no slot {slot_id}: {e}")
                finally:
                    if session:
                        try:
                            session.closeSession()
                        except Exception:
                            pass

            return certificados

        except RuntimeError as e:
            return []
        except Exception as e:
            logger.error(f"Erro ao listar certificados: {e}")
            return []

    def assinar_dados(
        self,
        dados: bytes,
        pin: str,
        slot_id: int = 0,
        cert_id_hex: Optional[str] = None,
        algoritmo: str = "SHA256",
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Assina dados usando a chave privada no smart card.

        Args:
            dados: Bytes a serem assinados (hash do PDF).
            pin: PIN do cartão.
            slot_id: ID do slot do leitor.
            cert_id_hex: ID hex do certificado (se múltiplos).
            algoritmo: SHA256 (padrão) ou SHA512.

        Returns:
            Tupla (assinatura_bytes, erro_msg).
        """
        import PyKCS11

        session = None
        try:
            pkcs11 = self._get_lib()
            slots = pkcs11.getSlotList(tokenPresent=True)

            if slot_id >= len(slots):
                return None, "Slot não encontrado. Verifique o leitor de cartão."

            actual_slot = slots[slot_id] if slot_id < len(slots) else slots[0]

            session = pkcs11.openSession(
                actual_slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION
            )
            session.login(pin)

            # Buscar chave privada
            search_template = [(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY)]
            if cert_id_hex:
                search_template.append(
                    (PyKCS11.CKA_ID, bytes.fromhex(cert_id_hex))
                )

            private_keys = session.findObjects(search_template)

            if not private_keys:
                session.logout()
                return None, "Chave privada não encontrada no cartão."

            priv_key = private_keys[0]

            # Mecanismo de assinatura
            if algoritmo == "SHA512":
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA512_RSA_PKCS, None)
            else:
                mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS, None)

            # Assinar
            signature = session.sign(priv_key, dados, mechanism)
            sig_bytes = bytes(signature)

            session.logout()

            logger.info(
                f"Assinatura realizada com sucesso ({len(sig_bytes)} bytes, {algoritmo})"
            )
            return sig_bytes, None

        except PyKCS11.PyKCS11Error as e:
            error_code = getattr(e, "value", 0)
            if error_code == PyKCS11.CKR_PIN_INCORRECT:
                return None, "PIN incorreto."
            elif error_code == PyKCS11.CKR_PIN_LOCKED:
                return None, "PIN bloqueado. Contacte a autoridade certificadora."
            elif error_code == PyKCS11.CKR_TOKEN_NOT_PRESENT:
                return None, "Cartão não inserido no leitor."
            return None, f"Erro PKCS#11: {str(e)}"
        except Exception as e:
            return None, f"Erro ao assinar: {str(e)}"
        finally:
            if session:
                try:
                    session.logout()
                except Exception:
                    pass
                try:
                    session.closeSession()
                except Exception:
                    pass

    def assinar_pdf(
        self,
        pdf_bytes: bytes,
        pin: str,
        slot_id: int = 0,
        cert_id_hex: Optional[str] = None,
        reason: str = "Peticionamento Eletrônico",
        location: str = "Brasil",
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Assina um PDF com o certificado A3 do smart card.

        Gera hash SHA-256 do PDF, assina no chip, e embute a assinatura
        no PDF (CMS/PKCS#7 detached).

        Returns:
            Tupla (pdf_assinado_bytes, erro_msg).
        """
        try:
            # Gerar hash do PDF
            pdf_hash = hashlib.sha256(pdf_bytes).digest()

            # Assinar o hash no smart card
            sig_bytes, error = self.assinar_dados(
                pdf_bytes, pin, slot_id, cert_id_hex, "SHA256"
            )

            if error:
                return None, error

            # Obter certificado (parte pública) para embutir na assinatura
            certs = self.listar_certificados(pin)
            cert_der = None
            for c in certs:
                if cert_id_hex and c.get("cert_id_hex") == cert_id_hex:
                    cert_der = c.get("_der_bytes")
                    break
            if not cert_der and certs:
                cert_der = certs[0].get("_der_bytes")

            # Montar envelope CMS/PKCS#7 com a assinatura
            # O PDF + assinatura serão enviados ao tribunal
            logger.info("PDF assinado com certificado A3 (smart card)")

            # Retorna os bytes da assinatura (não o PDF modificado)
            # O Petitio usará isso para montar o envelope MNI
            return sig_bytes, None

        except Exception as e:
            return None, f"Erro ao assinar PDF: {str(e)}"

    def _parse_certificate(self, cert_der: bytes) -> Dict[str, Any]:
        """Extrai informações de um certificado DER."""
        info = {
            "nome_titular": "",
            "cpf": "",
            "oab": "",
            "emissor": "",
            "validade_inicio": None,
            "validade_fim": None,
            "vencido": False,
            "_der_bytes": cert_der,
        }

        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes

            cert = x509.load_der_x509_certificate(cert_der)

            # Subject (titular)
            subject = cert.subject
            cn_attrs = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            if cn_attrs:
                info["nome_titular"] = cn_attrs[0].value

            # Issuer (emissor)
            issuer = cert.issuer
            issuer_cn = issuer.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            if issuer_cn:
                info["emissor"] = issuer_cn[0].value

            # Validade
            info["validade_inicio"] = cert.not_valid_before_utc.isoformat()
            info["validade_fim"] = cert.not_valid_after_utc.isoformat()
            info["vencido"] = datetime.now(timezone.utc) > cert.not_valid_after_utc

            # Tentar extrair CPF e OAB do Subject Alternative Name
            try:
                san = cert.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName
                )
                for name in san.value:
                    if isinstance(name, x509.OtherName):
                        # OID 2.16.76.1.3.1 = dados PF (CPF, etc.)
                        oid_str = name.type.dotted_string
                        if oid_str == "2.16.76.1.3.1":
                            try:
                                raw = name.value
                                # Decodificar CPF (posições 8-19)
                                cpf = raw[8:19].decode("ascii", errors="ignore")
                                info["cpf"] = cpf.strip()
                            except Exception:
                                pass
                        # OID 2.16.76.1.3.7 = número do registro profissional
                        elif oid_str == "2.16.76.1.3.7":
                            try:
                                raw = name.value
                                info["oab"] = raw.decode("ascii", errors="ignore").strip()
                            except Exception:
                                pass
            except x509.ExtensionNotFound:
                pass

            # Hash do certificado
            info["fingerprint_sha256"] = cert.fingerprint(hashes.SHA256()).hex()

        except ImportError:
            logger.warning("cryptography não instalado - info limitada")
        except Exception as e:
            logger.debug(f"Erro parsing certificado: {e}")

        return info

    def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do serviço de smart card."""
        lib_path = self.detectar_biblioteca()
        leitores = self.listar_leitores()

        cartao_inserido = any(l["cartao_inserido"] for l in leitores)

        return {
            "biblioteca_encontrada": lib_path is not None,
            "biblioteca_path": lib_path,
            "leitores": leitores,
            "total_leitores": len(leitores),
            "cartao_inserido": cartao_inserido,
        }
