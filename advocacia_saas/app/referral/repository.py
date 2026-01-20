"""
Repositório para programa de indicação
"""


from typing import List, Optional

from app import db
from app.models import Payment, Referral, User


class ReferralRepository:
    """Repositório para Indicações."""

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
    def get_converted_referrals(referrer_id: int) -> List[Referral]:
        """Lista referrals que se converteram em pagamentos."""
        return (
            Referral.query.join(User, Referral.user_id == User.id)
            .filter(User.referred_by == Referral.referral_code)
            .filter(Referral.user_id == referrer_id)
            .all()
        )

    @staticmethod
    def create(user_id: int, referral_code: str) -> Referral:
        """Cria novo referral."""
        referral = Referral(user_id=user_id, referral_code=referral_code)
        db.session.add(referral)
        db.session.commit()
        return referral

    @staticmethod
    def update_stats(
        referral: Referral, total_referrals: int = None, converted_referrals: int = None
    ) -> Referral:
        """Atualiza estatísticas do referral."""
        if total_referrals is not None:
            referral.total_referrals = total_referrals
        if converted_referrals is not None:
            referral.converted_referrals = converted_referrals
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
