"""
Serviço de gestão de certificados digitais A1 (.pfx).

Responsável por:
- Upload, validação e criptografia do certificado
- Extração de metadados (titular, OAB, validade, emissor)
- Descriptografia temporária para uso com EPROC
- Gerenciamento de senha (cofre criptografado)
"""

import hashlib
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from flask import current_app

from app import db
from app.models import AdvogadoCertificado

logger = logging.getLogger(__name__)


def _get_fernet():
    """Obtém instância Fernet com chave de criptografia."""
    from cryptography.fernet import Fernet

    key = os.environ.get("CERT_ENCRYPTION_KEY")
    if not key:
        # Gerar e avisar que precisa ser configurada
        logger.error(
            "CERT_ENCRYPTION_KEY não configurada! "
            "Gere uma chave com: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
        raise ValueError("CERT_ENCRYPTION_KEY não está configurada no ambiente.")
    return Fernet(key.encode() if isinstance(key, str) else key)


class CertificadoService:
    """Serviço para gestão de certificados digitais."""

    @classmethod
    def upload_certificado(
        cls,
        user_id: int,
        pfx_file,
        senha_pfx: str,
        apelido: str = "",
        salvar_senha: bool = False,
    ) -> Dict[str, Any]:
        """
        Faz upload e validação do certificado digital.

        Args:
            user_id: ID do usuário
            pfx_file: Arquivo .pfx (FileStorage do Flask)
            senha_pfx: Senha do certificado
            apelido: Nome amigável (opcional)
            salvar_senha: Se True, armazena senha criptografada

        Returns:
            Dict com success, message, e certificado (se ok)
        """
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography.x509.oid import NameOID
        except ImportError:
            return {
                "success": False,
                "message": "Biblioteca 'cryptography' não instalada.",
            }

        # Ler arquivo
        pfx_data = pfx_file.read()

        if not pfx_data:
            return {"success": False, "message": "Arquivo vazio."}

        if len(pfx_data) > 10 * 1024 * 1024:  # 10MB max
            return {"success": False, "message": "Arquivo muito grande (máx 10MB)."}

        # Validar que é um .pfx válido
        try:
            private_key, certificate, chain = pkcs12.load_key_and_certificates(
                pfx_data, senha_pfx.encode()
            )
        except ValueError:
            return {
                "success": False,
                "message": "Senha incorreta ou arquivo .pfx inválido.",
            }
        except Exception as e:
            logger.error(f"Erro ao abrir PFX: {e}")
            return {
                "success": False,
                "message": "Não foi possível abrir o certificado. Verifique o arquivo e a senha.",
            }

        if certificate is None:
            return {"success": False, "message": "Certificado não encontrado no arquivo .pfx."}

        # Extrair metadados do certificado
        subject = certificate.subject
        issuer = certificate.issuer

        nome_titular = cls._get_oid_value(subject, NameOID.COMMON_NAME) or ""
        email = cls._get_oid_value(subject, NameOID.EMAIL_ADDRESS) or ""
        organizacao = cls._get_oid_value(subject, NameOID.ORGANIZATION_NAME) or ""
        emissor_cn = cls._get_oid_value(issuer, NameOID.COMMON_NAME) or ""
        emissor_org = cls._get_oid_value(issuer, NameOID.ORGANIZATION_NAME) or ""

        validade_inicio = certificate.not_valid_before_utc
        validade_fim = certificate.not_valid_after_utc
        numero_serie = str(certificate.serial_number)

        # Extrair OAB e CPF do Subject (formato ICP-Brasil)
        oab_numero, oab_uf = cls._extract_oab(nome_titular, subject)
        cpf = cls._extract_cpf(nome_titular, subject)

        # Verificar validade
        agora = datetime.now(timezone.utc)
        if validade_fim.replace(tzinfo=timezone.utc) < agora:
            return {
                "success": False,
                "message": f"Certificado já vencido em {validade_fim.strftime('%d/%m/%Y')}.",
            }

        # Verificar duplicata (pelo hash)
        pfx_hash = hashlib.sha256(pfx_data).hexdigest()
        existente = AdvogadoCertificado.query.filter_by(
            user_id=user_id, certificado_hash=pfx_hash
        ).first()
        if existente:
            return {
                "success": False,
                "message": "Este certificado já está cadastrado.",
            }

        # Criptografar o .pfx
        try:
            fernet = _get_fernet()
            pfx_criptografado = fernet.encrypt(pfx_data)
        except Exception as e:
            logger.error(f"Erro ao criptografar PFX: {e}")
            return {
                "success": False,
                "message": "Erro interno ao proteger o certificado. Contate o suporte.",
            }

        # Criptografar senha se solicitado
        senha_cifrada = None
        if salvar_senha:
            try:
                senha_cifrada = fernet.encrypt(senha_pfx.encode())
            except Exception as e:
                logger.error(f"Erro ao criptografar senha: {e}")
                # Não é fatal — continua sem salvar senha

        # Criar registro
        if not apelido:
            apelido = f"{nome_titular[:50]}" if nome_titular else "Certificado A1"

        cert = AdvogadoCertificado(
            user_id=user_id,
            nome_titular=nome_titular[:300],
            oab_numero=oab_numero,
            oab_uf=oab_uf,
            cpf=cpf,
            emissor=f"{emissor_cn} ({emissor_org})"[:300],
            numero_serie=numero_serie[:100],
            certificado_pfx=pfx_criptografado,
            certificado_hash=pfx_hash,
            senha_cifrada=senha_cifrada,
            validade_inicio=validade_inicio,
            validade_fim=validade_fim,
            ativo=True,
            apelido=apelido[:100],
        )

        db.session.add(cert)
        db.session.commit()

        logger.info(
            f"Certificado cadastrado: user={user_id}, titular={nome_titular}, "
            f"OAB/{oab_uf} {oab_numero}, validade até {validade_fim.strftime('%d/%m/%Y')}"
        )

        return {
            "success": True,
            "message": "Certificado cadastrado com sucesso!",
            "certificado": cert,
        }

    @classmethod
    def get_certificados(cls, user_id: int):
        """Lista certificados do usuário."""
        return (
            AdvogadoCertificado.query
            .filter_by(user_id=user_id)
            .order_by(AdvogadoCertificado.ativo.desc(), AdvogadoCertificado.validade_fim.desc())
            .all()
        )

    @classmethod
    def get_certificado_ativo(cls, user_id: int) -> Optional[AdvogadoCertificado]:
        """Retorna o certificado ativo do usuário (mais recente)."""
        return (
            AdvogadoCertificado.query
            .filter_by(user_id=user_id, ativo=True)
            .order_by(AdvogadoCertificado.validade_fim.desc())
            .first()
        )

    @classmethod
    def descriptografar_pfx(
        cls,
        certificado: AdvogadoCertificado,
        senha_pfx: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Descriptografa o .pfx e salva em arquivo temporário.

        Args:
            certificado: Registro do certificado
            senha_pfx: Senha do certificado (usa a salva se não fornecida)

        Returns:
            Tupla (caminho_pfx_temp, senha) ou (None, None) em caso de erro.
            IMPORTANTE: o caller deve deletar o arquivo temporário após uso!
        """
        try:
            fernet = _get_fernet()

            # Descriptografar .pfx
            pfx_data = fernet.decrypt(certificado.certificado_pfx)

            # Obter senha
            if not senha_pfx and certificado.senha_cifrada:
                senha_pfx = fernet.decrypt(certificado.senha_cifrada).decode()

            if not senha_pfx:
                return None, None

            # Salvar em arquivo temporário
            tmp = tempfile.NamedTemporaryFile(
                suffix=".pfx", delete=False, prefix="petitio_cert_"
            )
            tmp.write(pfx_data)
            tmp.close()

            # Registrar uso
            certificado.registrar_uso()
            db.session.commit()

            return tmp.name, senha_pfx

        except Exception as e:
            logger.error(f"Erro ao descriptografar certificado {certificado.id}: {e}")
            return None, None

    @classmethod
    def remover_certificado(cls, certificado_id: int, user_id: int) -> Dict[str, Any]:
        """Remove um certificado (soft delete — desativa)."""
        cert = AdvogadoCertificado.query.filter_by(
            id=certificado_id, user_id=user_id
        ).first()

        if not cert:
            return {"success": False, "message": "Certificado não encontrado."}

        cert.ativo = False
        db.session.commit()

        logger.info(f"Certificado {certificado_id} desativado por user {user_id}")

        return {"success": True, "message": "Certificado removido com sucesso."}

    @classmethod
    def reativar_certificado(cls, certificado_id: int, user_id: int) -> Dict[str, Any]:
        """Reativa um certificado desativado."""
        cert = AdvogadoCertificado.query.filter_by(
            id=certificado_id, user_id=user_id
        ).first()

        if not cert:
            return {"success": False, "message": "Certificado não encontrado."}

        if cert.esta_vencido:
            return {"success": False, "message": "Não é possível reativar certificado vencido."}

        cert.ativo = True
        db.session.commit()

        return {"success": True, "message": "Certificado reativado."}

    @classmethod
    def excluir_certificado(cls, certificado_id: int, user_id: int) -> Dict[str, Any]:
        """Exclui permanentemente um certificado."""
        cert = AdvogadoCertificado.query.filter_by(
            id=certificado_id, user_id=user_id
        ).first()

        if not cert:
            return {"success": False, "message": "Certificado não encontrado."}

        db.session.delete(cert)
        db.session.commit()

        logger.info(f"Certificado {certificado_id} excluído por user {user_id}")

        return {"success": True, "message": "Certificado excluído permanentemente."}

    @classmethod
    def limpar_temp(cls, temp_path: str):
        """Remove arquivo temporário de certificado."""
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Erro ao limpar temp {temp_path}: {e}")

    # =========================================================================
    # UTILITÁRIOS INTERNOS
    # =========================================================================

    @staticmethod
    def _get_oid_value(name, oid):
        """Extrai valor de um OID do subject/issuer."""
        try:
            attrs = name.get_attributes_for_oid(oid)
            if attrs:
                return attrs[0].value
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_oab(nome: str, subject) -> Tuple[str, str]:
        """Extrai número da OAB e UF do nome do certificado."""
        # Padrão ICP-Brasil: "NOME DO ADVOGADO:12345/OAB-SC"
        # ou: "NOME DO ADVOGADO:OAB/SC 12345"
        if not nome:
            return "", ""

        patterns = [
            r"OAB[/-](\w{2})\s*(\d+)",        # OAB-SC 12345 ou OAB/SC 12345
            r"(\d+)/OAB[/-](\w{2})",           # 12345/OAB-SC
            r":(\d+)\s*/\s*OAB[/-](\w{2})",    # :12345/OAB-SC
        ]

        for pattern in patterns:
            match = re.search(pattern, nome, re.IGNORECASE)
            if match:
                groups = match.groups()
                if groups[0].isdigit():
                    return groups[0], groups[1].upper()
                else:
                    return groups[1], groups[0].upper()

        return "", ""

    @staticmethod
    def _extract_cpf(nome: str, subject) -> str:
        """Extrai CPF do nome do certificado ou OID."""
        if not nome:
            return ""

        # Tentar extrair CPF do CN — formato ICP-Brasil: "NOME:CPF"
        match = re.search(r":(\d{11})", nome)
        if match:
            cpf = match.group(1)
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"

        # Tentar do Subject alternativo
        try:
            from cryptography.x509.oid import NameOID

            # OID 2.16.76.1.3.1 = CPF no padrão ICP-Brasil
            attrs = subject.get_attributes_for_oid(
                NameOID.SERIAL_NUMBER
            )
            if attrs:
                serial = attrs[0].value
                cpf_match = re.search(r"(\d{11})", serial)
                if cpf_match:
                    cpf = cpf_match.group(1)
                    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"
        except Exception:
            pass

        return ""
