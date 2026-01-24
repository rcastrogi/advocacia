"""
Admin Repository - Camada de acesso a dados para administração
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_

from app import db
from app.models import (
    AICreditConfig,
    AIGeneration,
    AIGenerationFeedback,
    AuditLog,
    CreditTransaction,
    Payment,
    PetitionModel,
    PetitionModelSection,
    PetitionSection,
    PetitionType,
    PetitionUsage,
    PromoCoupon,
    RoadmapCategory,
    RoadmapFeedback,
    RoadmapItem,
    SavedPetition,
    TemplateExample,
    User,
    UserCredits,
)


# =============================================================================
# SESSION MANAGER
# =============================================================================


class AdminSessionManager:
    """Gerenciador de sessão para operações administrativas"""

    @staticmethod
    def commit():
        """Confirma todas as alterações pendentes"""
        db.session.commit()

    @staticmethod
    def rollback():
        """Desfaz todas as alterações pendentes"""
        db.session.rollback()


# =============================================================================
# USER REPOSITORIES
# =============================================================================


class UserAdminRepository:
    """Repositório para gerenciamento de usuários no admin"""

    @staticmethod
    def get_by_id(user_id: int) -> User | None:
        """Obtém usuário pelo ID"""
        return db.session.get(User, user_id)

    @staticmethod
    def get_filtered(
        search: str | None = None,
        status_filter: str = "all",
        user_type_filter: str = "all",
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ):
        """Obtém query de usuários filtrados"""
        query = User.query

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                    User.oab_number.ilike(search_term),
                )
            )

        if status_filter == "active":
            query = query.filter(User.is_active.is_(True))
        elif status_filter == "inactive":
            query = query.filter(User.is_active.is_(False))
        elif status_filter == "delinquent":
            query = query.filter(User.billing_status == "delinquent")
        elif status_filter == "trial":
            query = query.filter(User.billing_status == "trial")

        if user_type_filter != "all":
            query = query.filter(User.user_type == user_type_filter)

        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        return query

    @staticmethod
    def toggle_status(user: User) -> bool:
        """Alterna status ativo/inativo do usuário"""
        user.is_active = not user.is_active
        db.session.commit()
        return user.is_active

    @staticmethod
    def count_by_status() -> dict[str, int]:
        """Conta usuários por status"""
        return {
            "total": User.query.count(),
            "active": User.query.filter(User.is_active.is_(True)).count(),
            "inactive": User.query.filter(User.is_active.is_(False)).count(),
            "trial": User.query.filter(User.billing_status == "trial").count(),
        }

    @staticmethod
    def count_new_in_period(days: int = 30) -> int:
        """Conta novos usuários no período"""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        return User.query.filter(User.created_at >= start_date).count()


class UserCreditsAdminRepository:
    """Repositório para créditos de usuário no admin"""

    @staticmethod
    def add_credits(user_id: int, amount: int, reason: str = "Bônus administrativo") -> int:
        """Adiciona créditos de IA para um usuário"""
        user_credits = UserCredits.get_or_create(user_id)
        new_balance = user_credits.add_credits(amount, source="bonus")

        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="bonus",
            amount=amount,
            balance_after=new_balance,
            description=f"Bônus admin: {reason}",
        )
        db.session.add(transaction)
        db.session.commit()

        return new_balance


# =============================================================================
# PETITION REPOSITORIES
# =============================================================================


class PetitionTypeAdminRepository:
    """Repositório para tipos de petição no admin"""

    @staticmethod
    def get_all():
        """Obtém todos os tipos de petição"""
        return PetitionType.query.order_by(PetitionType.name.asc()).all()

    @staticmethod
    def get_by_id(type_id: int) -> PetitionType | None:
        """Obtém tipo pelo ID"""
        return db.session.get(PetitionType, type_id)

    @staticmethod
    def create(data: dict[str, Any]) -> PetitionType:
        """Cria novo tipo de petição"""
        petition_type = PetitionType(**data)
        db.session.add(petition_type)
        db.session.commit()
        return petition_type

    @staticmethod
    def update(petition_type: PetitionType, data: dict[str, Any]) -> PetitionType:
        """Atualiza tipo de petição"""
        for key, value in data.items():
            if hasattr(petition_type, key):
                setattr(petition_type, key, value)
        db.session.commit()
        return petition_type

    @staticmethod
    def delete(petition_type: PetitionType) -> None:
        """Exclui tipo de petição"""
        db.session.delete(petition_type)
        db.session.commit()

    @staticmethod
    def count() -> int:
        """Conta tipos de petição"""
        return PetitionType.query.count()


class PetitionModelAdminRepository:
    """Repositório para modelos de petição no admin"""

    @staticmethod
    def get_all():
        """Obtém todos os modelos"""
        return PetitionModel.query.order_by(PetitionModel.name.asc()).all()

    @staticmethod
    def get_by_id(model_id: int) -> PetitionModel | None:
        """Obtém modelo pelo ID"""
        return db.session.get(PetitionModel, model_id)

    @staticmethod
    def create(data: dict[str, Any]) -> PetitionModel:
        """Cria novo modelo"""
        model = PetitionModel(**data)
        db.session.add(model)
        db.session.commit()
        return model

    @staticmethod
    def update(model: PetitionModel, data: dict[str, Any]) -> PetitionModel:
        """Atualiza modelo"""
        for key, value in data.items():
            if hasattr(model, key):
                setattr(model, key, value)
        db.session.commit()
        return model

    @staticmethod
    def delete(model: PetitionModel) -> None:
        """Exclui modelo e suas associações"""
        PetitionModelSection.query.filter_by(petition_model_id=model.id).delete()
        db.session.delete(model)
        db.session.commit()

    @staticmethod
    def add_sections(model: PetitionModel, section_ids: list[int]) -> None:
        """Adiciona seções ao modelo na ordem especificada"""
        for order, section_id in enumerate(section_ids, 1):
            section = db.session.get(PetitionSection, section_id)
            if section:
                model_section = PetitionModelSection(
                    petition_model=model, section=section, order=order
                )
                db.session.add(model_section)
        db.session.commit()

    @staticmethod
    def clear_sections(model: PetitionModel) -> None:
        """Remove todas as seções do modelo"""
        PetitionModelSection.query.filter_by(petition_model_id=model.id).delete()
        db.session.commit()

    @staticmethod
    def add_section(model: PetitionModel, section: PetitionSection, order: int) -> PetitionModelSection:
        """Adiciona uma seção ao modelo"""
        model_section = PetitionModelSection(
            petition_model=model, section=section, order=order
        )
        db.session.add(model_section)
        db.session.commit()
        return model_section

    @staticmethod
    def remove_section(model_section: PetitionModelSection) -> None:
        """Remove uma seção do modelo"""
        db.session.delete(model_section)
        db.session.commit()

    @staticmethod
    def reorder_sections(model: PetitionModel, section_ids: list[int]) -> None:
        """Reordena seções do modelo"""
        for order, section_id in enumerate(section_ids, 1):
            model_section = PetitionModelSection.query.filter_by(
                petition_model_id=model.id, section_id=section_id
            ).first()
            if model_section:
                model_section.order = order
        db.session.commit()


class PetitionSectionAdminRepository:
    """Repositório para seções de petição no admin"""

    @staticmethod
    def get_all():
        """Obtém todas as seções"""
        return PetitionSection.query.order_by(PetitionSection.name.asc()).all()

    @staticmethod
    def get_by_id(section_id: int) -> PetitionSection | None:
        """Obtém seção pelo ID"""
        return db.session.get(PetitionSection, section_id)

    @staticmethod
    def get_by_ids(ids: list[int]) -> list[PetitionSection]:
        """Obtém seções por lista de IDs"""
        return PetitionSection.query.filter(PetitionSection.id.in_(ids)).all()

    @staticmethod
    def create(data: dict[str, Any]) -> PetitionSection:
        """Cria nova seção"""
        section = PetitionSection(**data)
        db.session.add(section)
        db.session.commit()
        return section

    @staticmethod
    def update(section: PetitionSection, data: dict[str, Any]) -> PetitionSection:
        """Atualiza seção"""
        for key, value in data.items():
            if hasattr(section, key):
                setattr(section, key, value)
        db.session.commit()
        return section

    @staticmethod
    def delete(section: PetitionSection) -> None:
        """Exclui seção e suas associações"""
        PetitionModelSection.query.filter_by(section_id=section.id).delete()
        db.session.delete(section)
        db.session.commit()


# =============================================================================
# ROADMAP REPOSITORIES
# =============================================================================


class RoadmapCategoryRepository:
    """Repositório para categorias do roadmap"""

    @staticmethod
    def get_all():
        """Obtém todas as categorias"""
        return RoadmapCategory.query.order_by(RoadmapCategory.order.asc()).all()

    @staticmethod
    def get_by_id(category_id: int) -> RoadmapCategory | None:
        """Obtém categoria pelo ID"""
        return db.session.get(RoadmapCategory, category_id)

    @staticmethod
    def create(data: dict[str, Any]) -> RoadmapCategory:
        """Cria nova categoria"""
        category = RoadmapCategory(**data)
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update(category: RoadmapCategory, data: dict[str, Any]) -> RoadmapCategory:
        """Atualiza categoria"""
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        db.session.commit()
        return category

    @staticmethod
    def delete(category: RoadmapCategory) -> None:
        """Exclui categoria"""
        db.session.delete(category)
        db.session.commit()


class RoadmapItemRepository:
    """Repositório para itens do roadmap"""

    @staticmethod
    def get_all(status: str | None = None, category_id: int | None = None):
        """Obtém todos os itens com filtros opcionais"""
        query = RoadmapItem.query

        if status:
            query = query.filter_by(status=status)
        if category_id:
            query = query.filter_by(category_id=category_id)

        return query.order_by(RoadmapItem.priority.desc(), RoadmapItem.created_at.desc()).all()

    @staticmethod
    def get_by_id(item_id: int) -> RoadmapItem | None:
        """Obtém item pelo ID"""
        return db.session.get(RoadmapItem, item_id)

    @staticmethod
    def create(data: dict[str, Any]) -> RoadmapItem:
        """Cria novo item"""
        item = RoadmapItem(**data)
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def update(item: RoadmapItem, data: dict[str, Any]) -> RoadmapItem:
        """Atualiza item"""
        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)
        db.session.commit()
        return item

    @staticmethod
    def delete(item: RoadmapItem) -> None:
        """Exclui item"""
        db.session.delete(item)
        db.session.commit()

    @staticmethod
    def toggle_visibility(item: RoadmapItem) -> bool:
        """Alterna visibilidade do item"""
        item.visible_to_users = not item.visible_to_users
        db.session.commit()
        return item.visible_to_users


class RoadmapFeedbackRepository:
    """Repositório para feedbacks do roadmap"""

    @staticmethod
    def get_all(status: str | None = None):
        """Obtém todos os feedbacks"""
        query = RoadmapFeedback.query

        if status:
            query = query.filter_by(status=status)

        return query.order_by(RoadmapFeedback.created_at.desc()).all()

    @staticmethod
    def get_by_id(feedback_id: int) -> RoadmapFeedback | None:
        """Obtém feedback pelo ID"""
        return db.session.get(RoadmapFeedback, feedback_id)

    @staticmethod
    def update_status(feedback: RoadmapFeedback, status: str) -> RoadmapFeedback:
        """Atualiza status do feedback"""
        feedback.status = status
        db.session.commit()
        return feedback

    @staticmethod
    def add_response(feedback: RoadmapFeedback, response: str) -> RoadmapFeedback:
        """Adiciona resposta ao feedback"""
        feedback.admin_response = response
        feedback.responded_at = datetime.now(timezone.utc)
        db.session.commit()
        return feedback

    @staticmethod
    def toggle_featured(feedback: RoadmapFeedback) -> bool:
        """Alterna destaque do feedback"""
        feedback.is_featured = not feedback.is_featured
        db.session.commit()
        return feedback.is_featured


# =============================================================================
# COUPON REPOSITORIES
# =============================================================================


class CouponRepository:
    """Repositório para cupons promocionais"""

    @staticmethod
    def get_all():
        """Obtém todos os cupons"""
        return PromoCoupon.query.order_by(PromoCoupon.created_at.desc()).all()

    @staticmethod
    def get_by_id(coupon_id: int) -> PromoCoupon | None:
        """Obtém cupom pelo ID"""
        return db.session.get(PromoCoupon, coupon_id)

    @staticmethod
    def get_by_code(code: str) -> PromoCoupon | None:
        """Obtém cupom pelo código"""
        return PromoCoupon.query.filter_by(code=code.upper()).first()

    @staticmethod
    def create(created_by_id: int, data: dict[str, Any]) -> PromoCoupon:
        """Cria novo cupom usando o método da classe"""
        return PromoCoupon.create_coupon(
            created_by_id=created_by_id,
            benefit_days=data.get("benefit_days", 0),
            benefit_credits=data.get("benefit_credits", 0),
            description=data.get("description"),
            expires_at=data.get("expires_at"),
            custom_code=data.get("code"),
        )

    @staticmethod
    def delete(coupon: PromoCoupon) -> None:
        """Exclui cupom"""
        db.session.delete(coupon)
        db.session.commit()

    @staticmethod
    def mark_used(coupon: PromoCoupon, user_id: int) -> None:
        """Marca cupom como usado"""
        coupon.is_used = True
        coupon.used_at = datetime.now(timezone.utc)
        coupon.used_by_id = user_id
        db.session.commit()


# =============================================================================
# AI CONFIG REPOSITORIES
# =============================================================================


class AICreditConfigRepository:
    """Repositório para configurações de créditos de IA"""

    @staticmethod
    def get_all():
        """Obtém todas as configurações"""
        return AICreditConfig.query.order_by(AICreditConfig.operation_key.asc()).all()

    @staticmethod
    def get_by_id(config_id: int) -> AICreditConfig | None:
        """Obtém configuração pelo ID"""
        return db.session.get(AICreditConfig, config_id)

    @staticmethod
    def update(config: AICreditConfig, data: dict[str, Any]) -> AICreditConfig:
        """Atualiza configuração"""
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        db.session.commit()
        return config

    @staticmethod
    def reset_to_defaults() -> int:
        """Reseta todas as configurações para padrão"""
        count = 0
        for default in AICreditConfig.DEFAULT_CONFIGS:
            config = AICreditConfig.query.filter_by(
                operation_key=default["operation_key"]
            ).first()
            if config:
                config.credit_cost = default["credit_cost"]
                config.is_premium = default["is_premium"]
                config.is_active = default["is_active"]
                count += 1
        db.session.commit()
        return count


# =============================================================================
# AUDIT LOG REPOSITORIES
# =============================================================================


class AuditLogRepository:
    """Repositório para logs de auditoria"""

    @staticmethod
    def get_filtered(
        entity_type: str | None = None,
        action: str | None = None,
        user_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ):
        """Obtém query de logs filtrados"""
        query = AuditLog.query

        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if action:
            query = query.filter_by(action=action)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return query.order_by(AuditLog.timestamp.desc())

    @staticmethod
    def get_by_id(log_id: int) -> AuditLog | None:
        """Obtém log pelo ID"""
        return db.session.get(AuditLog, log_id)

    @staticmethod
    def get_by_entity(entity_type: str, entity_id: int):
        """Obtém logs de uma entidade específica"""
        return (
            AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(AuditLog.timestamp.desc())
            .all()
        )


# =============================================================================
# DASHBOARD METRICS REPOSITORIES
# =============================================================================


class DashboardMetricsRepository:
    """Repositório para métricas do dashboard"""

    @staticmethod
    def get_petition_stats() -> dict[str, int]:
        """Obtém estatísticas de petições"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return {
            "total": PetitionUsage.query.count(),
            "month": PetitionUsage.query.filter(PetitionUsage.generated_at >= month_start).count(),
            "saved_total": SavedPetition.query.count(),
        }

    @staticmethod
    def get_ai_stats() -> dict[str, int]:
        """Obtém estatísticas de uso de IA"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return {
            "total": AIGeneration.query.count(),
            "month": AIGeneration.query.filter(AIGeneration.created_at >= month_start).count(),
        }

    @staticmethod
    def get_payment_stats() -> dict[str, Any]:
        """Obtém estatísticas de pagamentos"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_revenue = (
            db.session.query(func.sum(Payment.amount))
            .filter(Payment.status == "approved")
            .scalar()
            or 0
        )

        month_revenue = (
            db.session.query(func.sum(Payment.amount))
            .filter(
                and_(
                    Payment.status == "approved",
                    Payment.paid_at >= month_start,
                )
            )
            .scalar()
            or 0
        )

        return {
            "total_revenue": float(total_revenue),
            "month_revenue": float(month_revenue),
            "payment_count": Payment.query.filter_by(status="approved").count(),
        }


# =============================================================================
# AI TRAINING REPOSITORIES
# =============================================================================


class TemplateExampleRepository:
    """Repositório para exemplos de templates"""

    @staticmethod
    def get_all():
        """Obtém todos os exemplos ordenados por qualidade e uso"""
        return TemplateExample.query.order_by(
            TemplateExample.quality_score.desc(), TemplateExample.usage_count.desc()
        ).all()

    @staticmethod
    def get_by_id(example_id: int) -> TemplateExample | None:
        """Obtém exemplo pelo ID"""
        return db.session.get(TemplateExample, example_id)

    @staticmethod
    def create(data: dict[str, Any]) -> TemplateExample:
        """Cria novo exemplo de template"""
        example = TemplateExample(**data)
        db.session.add(example)
        db.session.commit()
        return example

    @staticmethod
    def update(example: TemplateExample, data: dict[str, Any]) -> TemplateExample:
        """Atualiza exemplo"""
        for key, value in data.items():
            if hasattr(example, key):
                setattr(example, key, value)
        db.session.commit()
        return example

    @staticmethod
    def delete(example: TemplateExample) -> None:
        """Exclui exemplo"""
        db.session.delete(example)
        db.session.commit()


class AIGenerationFeedbackRepository:
    """Repositório para feedbacks de geração de IA"""

    @staticmethod
    def create(data: dict[str, Any]) -> AIGenerationFeedback:
        """Cria novo feedback"""
        feedback = AIGenerationFeedback(**data)
        db.session.add(feedback)
        db.session.commit()
        return feedback

    @staticmethod
    def get_by_id(feedback_id: int) -> AIGenerationFeedback | None:
        """Obtém feedback pelo ID"""
        return db.session.get(AIGenerationFeedback, feedback_id)
