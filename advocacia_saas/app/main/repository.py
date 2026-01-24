"""
Main Repository - Camada de acesso a dados
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app import db
from app.models import (
    BillingPlan,
    Client,
    Notification,
    NotificationPreferences,
    PetitionType,
    PetitionUsage,
    RoadmapFeedback,
    RoadmapItem,
    TablePreference,
    Testimonial,
)


class ClientRepository:
    """Repositório para clientes"""

    @staticmethod
    def count_by_lawyer(lawyer_id: int) -> int:
        return Client.query.filter_by(lawyer_id=lawyer_id).count()

    @staticmethod
    def get_recent_by_lawyer(lawyer_id: int, limit: int = 5) -> list[Client]:
        return (
            Client.query.filter_by(lawyer_id=lawyer_id)
            .order_by(Client.created_at.desc())
            .limit(limit)
            .all()
        )


class TestimonialRepository:
    """Repositório para depoimentos"""

    @staticmethod
    def get_by_id(testimonial_id: int) -> Testimonial | None:
        return db.session.get(Testimonial, testimonial_id)

    @staticmethod
    def get_approved(limit: int = 6, featured_only: bool = False) -> list[Testimonial]:
        query = Testimonial.query.filter_by(status="approved")
        if featured_only:
            query = query.filter_by(is_featured=True)
        return (
            query.order_by(
                Testimonial.is_featured.desc(), Testimonial.created_at.desc()
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_user(user_id: int) -> list[Testimonial]:
        return (
            Testimonial.query.filter_by(user_id=user_id)
            .order_by(Testimonial.created_at.desc())
            .all()
        )

    @staticmethod
    def get_all_with_filter(status: str | None = None) -> list[Testimonial]:
        query = Testimonial.query
        if status and status != "all":
            query = query.filter_by(status=status)
        return query.order_by(Testimonial.created_at.desc()).all()

    @staticmethod
    def get_counts() -> dict[str, int]:
        return {
            "pending": Testimonial.query.filter_by(status="pending").count(),
            "approved": Testimonial.query.filter_by(status="approved").count(),
            "rejected": Testimonial.query.filter_by(status="rejected").count(),
        }

    @staticmethod
    def create(data: dict[str, Any]) -> Testimonial:
        testimonial = Testimonial(
            user_id=data["user_id"],
            content=data["content"],
            rating=data["rating"],
            display_name=data["display_name"],
            display_role=data.get("display_role"),
            display_location=data.get("display_location"),
            status="pending",
        )
        db.session.add(testimonial)
        db.session.commit()
        return testimonial

    @staticmethod
    def update(testimonial: Testimonial, data: dict[str, Any]) -> Testimonial:
        testimonial.content = data["content"]
        testimonial.rating = data["rating"]
        testimonial.display_name = data["display_name"]
        testimonial.display_role = data.get("display_role")
        testimonial.display_location = data.get("display_location")
        testimonial.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return testimonial

    @staticmethod
    def delete(testimonial: Testimonial) -> None:
        db.session.delete(testimonial)
        db.session.commit()

    @staticmethod
    def moderate(
        testimonial: Testimonial,
        action: str,
        moderator_id: int,
        rejection_reason: str | None = None,
    ) -> Testimonial:
        if action == "approve":
            testimonial.status = "approved"
            testimonial.rejection_reason = None
        elif action == "reject":
            testimonial.status = "rejected"
            testimonial.rejection_reason = rejection_reason
        elif action == "feature":
            testimonial.is_featured = not testimonial.is_featured

        if action in ["approve", "reject"]:
            testimonial.moderated_by = moderator_id
            testimonial.moderated_at = datetime.now(timezone.utc)

        db.session.commit()
        return testimonial


class RoadmapRepository:
    """Repositório para roadmap"""

    @staticmethod
    def get_public_items() -> list[RoadmapItem]:
        return RoadmapItem.query.filter_by(visible_to_users=True).all()

    @staticmethod
    def get_by_slug(slug: str, public_only: bool = True) -> RoadmapItem | None:
        query = RoadmapItem.query.filter_by(slug=slug)
        if public_only:
            query = query.filter_by(visible_to_users=True)
        return query.first()

    @staticmethod
    def get_completed_items(limit: int = 3) -> list[RoadmapItem]:
        return (
            RoadmapItem.query.filter_by(visible_to_users=True, status="completed")
            .order_by(RoadmapItem.actual_completion_date.desc().nullslast())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_in_progress_items(limit: int = 3) -> list[RoadmapItem]:
        return (
            RoadmapItem.query.filter_by(visible_to_users=True, status="in_progress")
            .order_by(RoadmapItem.priority.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_planned_items(limit: int = 6) -> list[RoadmapItem]:
        return (
            RoadmapItem.query.filter_by(visible_to_users=True, status="planned")
            .order_by(
                RoadmapItem.priority.desc(),
                RoadmapItem.planned_completion_date.asc().nullslast(),
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_related_items(item: RoadmapItem, limit: int = 5) -> list[RoadmapItem]:
        return (
            RoadmapItem.query.filter(
                RoadmapItem.category_id == item.category_id,
                RoadmapItem.id != item.id,
                RoadmapItem.visible_to_users.is_(True),
            )
            .limit(limit)
            .all()
        )


class RoadmapFeedbackRepository:
    """Repositório para feedback do roadmap"""

    @staticmethod
    def get_by_user_and_item(user_id: int, item_id: int) -> RoadmapFeedback | None:
        return RoadmapFeedback.query.filter_by(
            roadmap_item_id=item_id, user_id=user_id
        ).first()

    @staticmethod
    def create(data: dict[str, Any]) -> RoadmapFeedback:
        feedback = RoadmapFeedback(
            roadmap_item_id=data["roadmap_item_id"],
            user_id=data["user_id"],
            rating=data["rating"],
            rating_category=data.get("rating_category"),
            title=data.get("title"),
            comment=data.get("comment"),
            pros=data.get("pros"),
            cons=data.get("cons"),
            suggestions=data.get("suggestions"),
            usage_frequency=data.get("usage_frequency"),
            ease_of_use=data.get("ease_of_use"),
            is_anonymous=data.get("is_anonymous", False),
            user_agent=data.get("user_agent"),
            ip_address=data.get("ip_address"),
            session_id=data.get("session_id"),
        )
        db.session.add(feedback)
        db.session.commit()
        return feedback

    @staticmethod
    def update(feedback: RoadmapFeedback, data: dict[str, Any]) -> RoadmapFeedback:
        feedback.rating = data["rating"]
        feedback.rating_category = data.get("rating_category")
        feedback.title = data.get("title")
        feedback.comment = data.get("comment")
        feedback.pros = data.get("pros")
        feedback.cons = data.get("cons")
        feedback.suggestions = data.get("suggestions")
        feedback.usage_frequency = data.get("usage_frequency")
        feedback.ease_of_use = data.get("ease_of_use")
        feedback.is_anonymous = data.get("is_anonymous", False)
        feedback.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return feedback


class NotificationRepository:
    """Repositório para notificações"""

    @staticmethod
    def get_by_user(user_id: int) -> list[Notification]:
        return (
            Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def get_unread_by_user(user_id: int) -> list[Notification]:
        return Notification.query.filter_by(user_id=user_id, read=False).all()

    @staticmethod
    def mark_as_read(notification: Notification) -> Notification:
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()
        return notification

    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        notifications = Notification.query.filter_by(user_id=user_id, read=False).all()
        now = datetime.now(timezone.utc)
        for n in notifications:
            n.read = True
            n.read_at = now
        db.session.commit()
        return len(notifications)


class NotificationPreferencesRepository:
    """Repositório para preferências de notificação"""

    @staticmethod
    def get_or_create(user_id: int) -> NotificationPreferences:
        return NotificationPreferences.get_or_create(user_id)

    @staticmethod
    def update(
        prefs: NotificationPreferences, data: dict[str, Any]
    ) -> NotificationPreferences:
        for key, value in data.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        db.session.commit()
        return prefs


class BillingPlanRepository:
    """Repositório para planos"""

    @staticmethod
    def get_active_plans() -> list[BillingPlan]:
        return (
            BillingPlan.query.filter_by(active=True)
            .order_by(BillingPlan.monthly_fee)
            .all()
        )


class PetitionTypeRepository:
    """Repositório para tipos de petição"""

    @staticmethod
    def get_implemented() -> list[PetitionType]:
        return (
            PetitionType.query.filter_by(is_implemented=True, is_active=True)
            .order_by(PetitionType.category, PetitionType.name)
            .all()
        )

    @staticmethod
    def get_dynamic_form_types() -> list[PetitionType]:
        return (
            PetitionType.query.filter_by(use_dynamic_form=True, is_active=True)
            .order_by(PetitionType.name)
            .all()
        )


class PetitionUsageRepository:
    """Repositório para uso de petições"""

    @staticmethod
    def count_by_cycle(user_id: int, cycle: str) -> int:
        return PetitionUsage.query.filter_by(
            user_id=user_id, billing_cycle=cycle
        ).count()

    @staticmethod
    def get_billable_amount(user_id: int, cycle: str) -> float:
        return (
            db.session.query(func.coalesce(func.sum(PetitionUsage.amount), 0))
            .filter(
                PetitionUsage.user_id == user_id,
                PetitionUsage.billing_cycle == cycle,
                PetitionUsage.billable.is_(True),
            )
            .scalar()
        ) or 0


class TablePreferenceRepository:
    """Repositório para preferências de tabela"""

    @staticmethod
    def get_for_user(user_id: int, view_key: str) -> dict | None:
        pref = TablePreference.query.filter_by(
            user_id=user_id, view_key=view_key
        ).first()
        return pref.preferences if pref else None

    @staticmethod
    def set_for_user(user_id: int, view_key: str, preferences: dict) -> None:
        TablePreference.set_for_user(user_id, view_key, preferences)
