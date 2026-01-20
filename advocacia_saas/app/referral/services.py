"""
Serviços para programa de indicação
"""

import logging
import secrets
from dataclasses import dataclass

from decimal import Decimal
from typing import Any, Dict, Optional

from flask import url_for

from app.models import User
from app.referral.repository import ReferralPaymentRepository, ReferralRepository

logger = logging.getLogger(__name__)


@dataclass
class ReferralStats:
    """Estatísticas de indicação."""

    total_referrals: int
    converted_referrals: int
    pending_referrals: int
    conversion_rate: float
    total_earnings: float
    referral_code: str
    referral_link: str


class ReferralCodeService:
    """Serviço para códigos de indicação."""

    @staticmethod
    def generate_code() -> str:
        """Gera um código de indicação único."""
        return secrets.token_urlsafe(8).upper()[:10]

    @staticmethod
    def validate_code(code: str) -> Dict[str, Any]:
        """Valida um código de indicação."""
        if not code or len(code) < 5:
            return {"valid": False, "error": "Código inválido"}

        referral = ReferralRepository.get_by_code(code.upper())

        if not referral:
            return {"valid": False, "error": "Código não encontrado"}

        return {
            "valid": True,
            "referral_code": referral.referral_code,
            "referrer_id": referral.user_id,
        }


class ReferralService:
    """Serviço principal de indicações."""

    COMMISSION_RATE = Decimal("0.10")  # 10% de comissão

    @staticmethod
    def get_or_create_referral(user: User) -> Any:
        """Obtém ou cria referral para um usuário."""
        referral = ReferralRepository.get_by_user(user.id)

        if not referral:
            code = ReferralCodeService.generate_code()
            referral = ReferralRepository.create(user.id, code)

        return referral

    @staticmethod
    def get_stats(user: User, _external: bool = False) -> ReferralStats:
        """Calcula estatísticas de indicação do usuário."""
        referral = ReferralService.get_or_create_referral(user)

        # Contar indicados
        referred_users = ReferralRepository.get_referred_users(referral)
        total_referrals = len(referred_users)

        # Contar conversões (pagamentos aprovados)
        payments = ReferralPaymentRepository.get_converted_payments(referral)
        converted_referrals = len(set(p.user_id for p in payments))

        # Calcular ganhos
        total_earnings = sum(
            float(p.amount) * float(ReferralService.COMMISSION_RATE) for p in payments
        )

        # Pendentes
        pending_referrals = total_referrals - converted_referrals

        # Taxa de conversão
        conversion_rate = (
            (converted_referrals / total_referrals * 100) if total_referrals > 0 else 0
        )

        # Link de indicação
        referral_link = url_for(
            "referral.landing",
            code=referral.referral_code,
            _external=_external,
        )

        return ReferralStats(
            total_referrals=total_referrals,
            converted_referrals=converted_referrals,
            pending_referrals=pending_referrals,
            conversion_rate=round(conversion_rate, 1),
            total_earnings=round(total_earnings, 2),
            referral_code=referral.referral_code,
            referral_link=referral_link,
        )

    @staticmethod
    def get_share_data(user: User) -> Dict[str, Any]:
        """Gera dados para compartilhamento."""
        referral = ReferralService.get_or_create_referral(user)

        referral_link = url_for(
            "referral.landing",
            code=referral.referral_code,
            _external=True,
        )

        share_message = (
            f"🎯 Use meu código {referral.referral_code} e ganhe 10% de desconto "
            f"no primeiro mês do Petitio! {referral_link}"
        )

        return {
            "referral_code": referral.referral_code,
            "referral_link": referral_link,
            "share_message": share_message,
            "whatsapp_link": f"https://wa.me/?text={share_message}",
            "telegram_link": f"https://t.me/share/url?url={referral_link}&text={share_message}",
        }


class ReferralProcessingService:
    """Serviço para processamento de indicações."""

    @staticmethod
    def process_registration(referred_by_code: str) -> Optional[Dict[str, Any]]:
        """Processa indicação no registro de novo usuário."""
        if not referred_by_code:
            return None

        referral = ReferralRepository.get_by_code(referred_by_code.upper())

        if not referral:
            logger.warning(f"Código de indicação inválido: {referred_by_code}")
            return None

        # Incrementar contador
        ReferralRepository.increment_referrals(referral)

        logger.info(f"Novo usuário indicado pelo código: {referred_by_code}")

        return {
            "referral_code": referral.referral_code,
            "referrer_id": referral.user_id,
        }

    @staticmethod
    def process_conversion(user: User) -> Optional[Dict[str, Any]]:
        """Processa conversão de indicação após pagamento."""
        if not user.referred_by:
            return None

        referral = ReferralRepository.get_by_code(user.referred_by)

        if not referral:
            logger.warning(f"Referral não encontrado para código: {user.referred_by}")
            return None

        # Incrementar conversões
        ReferralRepository.increment_conversions(referral)

        logger.info(f"Conversão processada para código: {user.referred_by}")

        return {
            "referral_code": referral.referral_code,
            "referrer_id": referral.user_id,
            "converted_user_id": user.id,
        }
