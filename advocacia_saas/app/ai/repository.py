"""
AI Repository - Camada de acesso a dados para créditos e gerações de IA
"""

import json
from datetime import datetime, timezone
from typing import Any

from app import db
from app.models import (
    AIGeneration,
    CreditPackage,
    CreditTransaction,
    UserCredits,
)


class UserCreditsRepository:
    """Repositório para créditos de usuário"""

    @staticmethod
    def get_or_create(user_id: int) -> UserCredits:
        return UserCredits.get_or_create(user_id)

    @staticmethod
    def has_credits(user_id: int, amount: int) -> bool:
        user_credits = UserCreditsRepository.get_or_create(user_id)
        return user_credits.has_credits(amount)

    @staticmethod
    def use_credits(user_id: int, amount: int) -> bool:
        user_credits = UserCreditsRepository.get_or_create(user_id)
        return user_credits.use_credits(amount)

    @staticmethod
    def add_credits(user_id: int, amount: int, source: str = "purchase") -> UserCredits:
        user_credits = UserCreditsRepository.get_or_create(user_id)
        user_credits.add_credits(amount, source)
        return user_credits


class CreditPackageRepository:
    """Repositório para pacotes de crédito"""

    @staticmethod
    def get_all_active() -> list[CreditPackage]:
        return (
            CreditPackage.query.filter_by(is_active=True)
            .order_by(CreditPackage.sort_order)
            .all()
        )

    @staticmethod
    def get_by_slug(slug: str) -> CreditPackage | None:
        return CreditPackage.query.filter_by(slug=slug, is_active=True).first()

    @staticmethod
    def get_by_id(package_id: int) -> CreditPackage | None:
        return db.session.get(CreditPackage, package_id)


class CreditTransactionRepository:
    """Repositório para transações de crédito"""

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[CreditTransaction]:
        return (
            CreditTransaction.query.filter_by(user_id=user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_user_paginated(user_id: int, page: int = 1, per_page: int = 50):
        return (
            CreditTransaction.query.filter_by(user_id=user_id)
            .order_by(CreditTransaction.created_at.desc())
            .paginate(page=page, per_page=per_page)
        )

    @staticmethod
    def get_by_payment_id(payment_id: str) -> CreditTransaction | None:
        return CreditTransaction.query.filter_by(
            payment_intent_id=str(payment_id)
        ).first()

    @staticmethod
    def create(data: dict[str, Any]) -> CreditTransaction:
        user_credits = UserCreditsRepository.get_or_create(data["user_id"])

        transaction = CreditTransaction(
            user_id=data["user_id"],
            transaction_type=data["transaction_type"],
            amount=data["amount"],
            balance_after=user_credits.balance,
            description=data.get("description", ""),
            package_id=data.get("package_id"),
            generation_id=data.get("generation_id"),
            payment_intent_id=data.get("payment_intent_id"),
            metadata=json.dumps(data.get("metadata")) if data.get("metadata") else None,
        )
        db.session.add(transaction)
        return transaction


class AIGenerationRepository:
    """Repositório para gerações de IA"""

    @staticmethod
    def get_by_user(user_id: int, limit: int = 20) -> list[AIGeneration]:
        return (
            AIGeneration.query.filter_by(user_id=user_id)
            .order_by(AIGeneration.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_user_paginated(user_id: int, page: int = 1, per_page: int = 20):
        return (
            AIGeneration.query.filter_by(user_id=user_id)
            .order_by(AIGeneration.created_at.desc())
            .paginate(page=page, per_page=per_page)
        )

    @staticmethod
    def count_by_user(user_id: int) -> int:
        return AIGeneration.query.filter_by(user_id=user_id).count()

    @staticmethod
    def get_by_id(generation_id: int, user_id: int) -> AIGeneration | None:
        return AIGeneration.query.filter_by(id=generation_id, user_id=user_id).first()

    @staticmethod
    def create(data: dict[str, Any]) -> AIGeneration:
        generation = AIGeneration(
            user_id=data["user_id"],
            generation_type=data["generation_type"],
            petition_type_slug=data.get("petition_type_slug"),
            section_name=data.get("section_name"),
            credits_used=data.get("credits_used", 0),
            model_used=data.get("model_used", "gpt-4o-mini"),
            tokens_input=data.get("tokens_input"),
            tokens_output=data.get("tokens_output"),
            tokens_total=data.get("tokens_total"),
            response_time_ms=data.get("response_time_ms"),
            input_data=json.dumps(data.get("input_data"))
            if data.get("input_data")
            else None,
            output_content=data.get("output_content"),
            status=data.get("status", "completed"),
            error_message=data.get("error_message"),
            completed_at=datetime.now(timezone.utc)
            if data.get("status") == "completed"
            else None,
            prompt=data.get("prompt"),
            result=data.get("result"),
            tokens_used=data.get("tokens_used"),
        )
        generation.calculate_cost()
        db.session.add(generation)
        return generation

    @staticmethod
    def update_feedback(
        generation: AIGeneration,
        rating: int | None = None,
        was_used: bool | None = None,
    ) -> None:
        if rating is not None:
            generation.user_rating = min(5, max(1, int(rating)))
        if was_used is not None:
            generation.was_used = bool(was_used)
        db.session.commit()


class AISessionManager:
    """Gerenciador de sessão para operações de IA"""

    @staticmethod
    def commit():
        """Confirma todas as alterações pendentes"""
        db.session.commit()

    @staticmethod
    def rollback():
        """Desfaz todas as alterações pendentes"""
        db.session.rollback()
