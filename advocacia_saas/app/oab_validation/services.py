"""
Serviços para validação de OAB
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.utils.oab_validator import consultar_oab_online

logger = logging.getLogger(__name__)


@dataclass
class OABValidationResult:
    """Resultado da validação de OAB."""

    valid: bool
    numero: Optional[str] = None
    uf: Optional[str] = None
    nome: Optional[str] = None
    situacao: Optional[str] = None
    error: Optional[str] = None


class OABValidationService:
    """Serviço para validação de registro OAB."""

    # Estados válidos
    VALID_UFS = [
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
    ]

    @staticmethod
    def sanitize_number(numero: str) -> str:
        """Sanitiza número de OAB."""
        if not numero:
            return ""
        # Remove caracteres não numéricos
        return re.sub(r"[^0-9]", "", numero)

    @staticmethod
    def validate_input(numero: str, uf: str) -> Optional[str]:
        """Valida inputs antes de consultar."""
        if not numero:
            return "Número da OAB é obrigatório"

        clean_numero = OABValidationService.sanitize_number(numero)
        if len(clean_numero) < 3 or len(clean_numero) > 8:
            return "Número da OAB deve ter entre 3 e 8 dígitos"

        if not uf:
            return "UF é obrigatória"

        if uf.upper() not in OABValidationService.VALID_UFS:
            return f"UF inválida: {uf}"

        return None

    @staticmethod
    def validate(numero: str, uf: str) -> OABValidationResult:
        """Valida registro OAB via API externa."""
        # Sanitizar inputs
        clean_numero = OABValidationService.sanitize_number(numero)
        clean_uf = uf.upper().strip() if uf else ""

        # Validar inputs
        error = OABValidationService.validate_input(clean_numero, clean_uf)
        if error:
            return OABValidationResult(valid=False, error=error)

        try:
            # Montar número completo (UF + número)
            full_oab = f"{clean_uf}{clean_numero}"

            # Consultar API
            result = consultar_oab_online(full_oab)

            if result.get("formato_valido"):
                return OABValidationResult(
                    valid=True,
                    numero=clean_numero,
                    uf=clean_uf,
                    nome=result.get("nome"),
                    situacao=result.get("situacao", "Formato válido"),
                )
            else:
                return OABValidationResult(
                    valid=False,
                    error=result.get("mensagem", "Registro não encontrado"),
                )

        except Exception as e:
            logger.error(f"Erro ao validar OAB: {str(e)}")
            return OABValidationResult(
                valid=False,
                error="Erro ao consultar API da OAB. Tente novamente.",
            )

    @staticmethod
    def format_oab(numero: str, uf: str) -> str:
        """Formata número de OAB para exibição."""
        clean_numero = OABValidationService.sanitize_number(numero)
        clean_uf = uf.upper().strip() if uf else ""
        return f"OAB/{clean_uf} {clean_numero}"

