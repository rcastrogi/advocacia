"""
Deadlines Repository - Camada de acesso a dados
"""

# json removed - unused
from datetime import datetime, timedelta, timezone
from typing import Any

from app import db
from app.models import AgendaBlock, Client, Deadline


class DeadlineRepository:
    """Repositório para prazos"""

    @staticmethod
    def get_by_id(deadline_id: int) -> Deadline | None:
        return Deadline.query.get(deadline_id)

    @staticmethod
    def get_by_user_filtered(
        user_id: int,
        status: str | None = None,
        deadline_type: str | None = None,
    ):
        """Retorna query filtrada para paginação"""
        query = Deadline.query.filter_by(user_id=user_id)

        if status and status != "all":
            query = query.filter_by(status=status)

        if deadline_type:
            query = query.filter_by(deadline_type=deadline_type)

        return query.order_by(Deadline.deadline_date.asc())

    @staticmethod
    def get_upcoming(user_id: int, days: int = 7, limit: int = 10) -> list[Deadline]:
        """Obtém próximos prazos"""
        deadline_date = datetime.now(timezone.utc) + timedelta(days=days)

        return (
            Deadline.query.filter(
                Deadline.user_id == user_id,
                Deadline.status == "pending",
                Deadline.deadline_date <= deadline_date,
            )
            .order_by(Deadline.deadline_date)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_pending_alerts() -> list[Deadline]:
        """Obtém prazos pendentes que precisam de alerta"""
        return Deadline.query.filter(
            Deadline.status == "pending",
            Deadline.alert_sent.is_(False),
        ).all()

    @staticmethod
    def create(data: dict[str, Any]) -> Deadline:
        deadline = Deadline(
            user_id=data["user_id"],
            title=data["title"],
            description=data.get("description"),
            deadline_type=data.get("deadline_type"),
            deadline_date=data["deadline_date"],
            alert_days_before=data.get("alert_days_before", 7),
            count_business_days=data.get("count_business_days", False),
            client_id=data.get("client_id"),
        )
        db.session.add(deadline)
        db.session.commit()
        return deadline

    @staticmethod
    def update(deadline: Deadline, data: dict[str, Any]) -> Deadline:
        for key, value in data.items():
            if hasattr(deadline, key):
                setattr(deadline, key, value)
        db.session.commit()
        return deadline

    @staticmethod
    def delete(deadline: Deadline) -> None:
        db.session.delete(deadline)
        db.session.commit()

    @staticmethod
    def mark_completed(deadline: Deadline, notes: str | None = None) -> None:
        deadline.mark_completed(notes=notes)

    @staticmethod
    def mark_alert_sent(deadline: Deadline) -> None:
        deadline.alert_sent = True
        deadline.alert_sent_at = datetime.now(timezone.utc)


class AgendaBlockRepository:
    """Repositório para bloqueios de agenda"""

    @staticmethod
    def get_by_id(block_id: int) -> AgendaBlock | None:
        return AgendaBlock.query.get(block_id)

    @staticmethod
    def get_by_user(user_id: int) -> list[AgendaBlock]:
        return (
            AgendaBlock.query.filter_by(user_id=user_id)
            .order_by(AgendaBlock.created_at.desc())
            .all()
        )

    @staticmethod
    def get_active_by_user(user_id: int) -> list[AgendaBlock]:
        return AgendaBlock.query.filter_by(user_id=user_id, is_active=True).all()

    @staticmethod
    def create(data: dict[str, Any]) -> AgendaBlock:
        block = AgendaBlock(
            user_id=data["user_id"],
            title=data["title"],
            description=data.get("description"),
            block_type=data.get("block_type", "recurring"),
            weekdays=data.get("weekdays"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            all_day=data.get("all_day", False),
            day_period=data.get("day_period"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            color=data.get("color", "#6c757d"),
            is_active=True,
        )
        db.session.add(block)
        db.session.commit()
        return block

    @staticmethod
    def update(block: AgendaBlock, data: dict[str, Any]) -> AgendaBlock:
        for key, value in data.items():
            if hasattr(block, key):
                setattr(block, key, value)
        db.session.commit()
        return block

    @staticmethod
    def delete(block: AgendaBlock) -> None:
        db.session.delete(block)
        db.session.commit()

    @staticmethod
    def toggle_active(block: AgendaBlock) -> bool:
        block.is_active = not block.is_active
        db.session.commit()
        return block.is_active


class ClientForDeadlineRepository:
    """Repositório para buscar clientes para prazos"""

    @staticmethod
    def get_by_user_ordered(user_id: int) -> list[Client]:
        return Client.query.filter_by(user_id=user_id).order_by(Client.full_name).all()
