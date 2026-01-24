"""
Repositório para programa de indicação
"""

from datetime import datetime, timezone
from typing import Any, List, Optional

from app import db
from app.models import Payment, Referral, ReferralCode, User


class ReferralCodeRepository:
    """Repositório para códigos de indicação."""

    @staticmethod
    def get_or_create(user: User) -> ReferralCode:
        """Obtém ou cria código de indicação para o usuário."""
        return ReferralCode.get_or_create(user)

    @staticmethod
    def get_by_code(code: str, active_only: bool = True) -> Optional[ReferralCode]:
        """Busca código de indicação pelo código."""
        query = ReferralCode.query.filter_by(code=code.upper())
        if active_only:
            query = query.filter_by(is_active=True)
        return query.first()

    @staticmethod
    def increment_clicks(referral_code: ReferralCode) -> None:
        """Incrementa cliques no código."""
        referral_code.increment_clicks()

    @staticmethod
    def increment_registrations(referral_code: ReferralCode) -> None:
        """Incrementa registros do código."""
        referral_code.increment_registrations()

    @staticmethod
    def increment_conversions(referral_code: ReferralCode) -> None:
        """Incrementa conversões do código."""
        referral_code.increment_conversions()


class ReferralRecordRepository:
    """Repositório para registros de indicação."""

    @staticmethod
    def get_by_referrer(referrer_id: int, limit: int = 20) -> List[Referral]:
        """Lista indicações feitas por um usuário."""
        return (
            Referral.query.filter_by(referrer_id=referrer_id)
            .order_by(Referral.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_email(email: str) -> Optional[Referral]:
        """Busca indicação por email."""
        return Referral.query.filter_by(referred_email=email.lower()).first()

    @staticmethod
    def get_user_stats(user_id: int) -> dict[str, Any]:
        """Obtém estatísticas de indicação do usuário."""
        return Referral.get_user_stats(user_id)

    @staticmethod
    def create(
        referrer_id: int,
        referred_id: int,
        referred_email: str,
        referral_code: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Referral:
        """Cria novo registro de indicação."""
        referral = Referral(
            referrer_id=referrer_id,
            referred_id=referred_id,
            referred_email=referred_email.lower(),
            referral_code=referral_code,
            status="registered",
            registered_at=datetime.now(timezone.utc),
            referred_ip=ip_address,
            referred_user_agent=user_agent[:500] if user_agent else None,
        )
        db.session.add(referral)
        db.session.commit()
        return referral

    @staticmethod
    def update_referred_user(referral: Referral, user_id: int) -> Referral:
        """Atualiza o usuário indicado."""
        referral.referred_id = user_id
        referral.status = "registered"
        referral.registered_at = datetime.now(timezone.utc)
        db.session.commit()
        return referral

    @staticmethod
    def process_conversion(user_id: int, payment_id: int, payment_amount) -> Optional[Referral]:
        """Processa conversão de indicação."""
        return Referral.process_conversion(user_id, payment_id, payment_amount)


class ReferralRepository:
    """Repositório legado - mantido para compatibilidade."""

    @staticmethod
    def get_by_user(user_id: int) -> Optional[Referral]:
        """Busca referral do usuário."""
        return Referral.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_by_code(code: str) -> Optional[Referral]:
        """Busca referral pelo código."""
        return Referral.query.filter_by(referral_code=code).first()

    @staticmethod
    def get_referred_users(referral: Referral) -> List[User]:
        """Lista usuários indicados por um referral."""
        return User.query.filter_by(referred_by=referral.referral_code).all()

    @staticmethod
    def create(user_id: int, referral_code: str) -> Referral:
        """Cria novo referral."""
        referral = Referral(user_id=user_id, referral_code=referral_code)
        db.session.add(referral)
        db.session.commit()
        return referral

    @staticmethod
    def increment_referrals(referral: Referral) -> Referral:
        """Incrementa contador de indicações."""
        referral.total_referrals = (referral.total_referrals or 0) + 1
        db.session.commit()
        return referral

    @staticmethod
    def increment_conversions(referral: Referral) -> Referral:
        """Incrementa contador de conversões."""
        referral.converted_referrals = (referral.converted_referrals or 0) + 1
        db.session.commit()
        return referral


class ReferralPaymentRepository:
    """Repositório para pagamentos de indicações."""

    @staticmethod
    def get_converted_payments(referrer: Referral) -> List[Payment]:
        """Lista pagamentos de usuários indicados."""
        referred_users = ReferralRepository.get_referred_users(referrer)
        referred_user_ids = [u.id for u in referred_users]

        if not referred_user_ids:
            return []

        return (
            Payment.query.filter(Payment.user_id.in_(referred_user_ids))
            .filter(Payment.status == "approved")
            .all()
        )
