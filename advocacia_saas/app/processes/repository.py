"""
Processes Repository - Camada de Acesso a Dados.

Operações de banco de dados para processos judiciais.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func

from app import db
from app.models import Client, Process, SavedPetition


class ProcessRepository:
    """Repositório para operações com processos."""

    @staticmethod
    def find_by_id(process_id: int) -> Optional[Process]:
        """Busca processo pelo ID."""
        return Process.query.get(process_id)

    @staticmethod
    def find_by_id_and_user(process_id: int, user_id: int) -> Optional[Process]:
        """Busca processo pelo ID e usuário."""
        return Process.query.filter_by(id=process_id, user_id=user_id).first()

    @staticmethod
    def find_by_number(process_number: str) -> Optional[Process]:
        """Busca processo pelo número."""
        return Process.query.filter_by(process_number=process_number).first()

    @staticmethod
    def count_by_user(user_id: int) -> int:
        """Conta total de processos do usuário."""
        return Process.query.filter_by(user_id=user_id).count()

    @staticmethod
    def count_by_status(user_id: int, status: str) -> int:
        """Conta processos por status."""
        return Process.query.filter_by(user_id=user_id, status=status).count()

    @staticmethod
    def get_recent(user_id: int, limit: int = 10) -> List[Process]:
        """Lista processos recentes."""
        return (
            Process.query.filter_by(user_id=user_id)
            .order_by(Process.updated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_with_urgent_deadlines(user_id: int, days: int = 7) -> int:
        """Conta processos com prazos urgentes."""
        today = date.today()
        deadline_limit = today + timedelta(days=days)

        return Process.query.filter(
            Process.user_id == user_id,
            Process.next_deadline.isnot(None),
            Process.next_deadline <= deadline_limit,
        ).count()

    @staticmethod
    def get_grouped_by_status(user_id: int) -> Dict[str, int]:
        """Agrupa processos por status."""
        results = (
            db.session.query(Process.status, func.count(Process.id).label("count"))
            .filter_by(user_id=user_id)
            .group_by(Process.status)
            .all()
        )
        return dict(results)

    @staticmethod
    def search(
        user_id: int,
        status: Optional[str] = None,
        search_term: Optional[str] = None,
    ):
        """Busca processos com filtros."""
        query = Process.query.filter_by(user_id=user_id)

        if status:
            query = query.filter_by(status=status)

        if search_term:
            query = query.filter(
                (Process.title.contains(search_term))
                | (Process.process_number.contains(search_term))
                | (Process.plaintiff.contains(search_term))
                | (Process.defendant.contains(search_term))
            )

        return query.order_by(Process.updated_at.desc())

    @staticmethod
    def create(user_id: int, **kwargs) -> Process:
        """Cria novo processo."""
        process = Process(user_id=user_id, **kwargs)
        db.session.add(process)
        db.session.commit()
        return process

    @staticmethod
    def update(process: Process, **kwargs) -> Process:
        """Atualiza processo existente."""
        for key, value in kwargs.items():
            if hasattr(process, key):
                setattr(process, key, value)
        db.session.commit()
        return process

    @staticmethod
    def delete(process: Process):
        """Remove processo."""
        db.session.delete(process)
        db.session.commit()


class PetitionRepository:
    """Repositório para petições no contexto de processos."""

    @staticmethod
    def get_without_process_number(user_id: int, limit: int = 10) -> List[SavedPetition]:
        """Lista petições sem número de processo."""
        return (
            SavedPetition.query.filter_by(user_id=user_id)
            .filter(
                (SavedPetition.process_number.is_(None))
                | (SavedPetition.process_number == "")
            )
            .filter(SavedPetition.status == "completed")
            .order_by(SavedPetition.completed_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_paginated_without_number(user_id: int, page: int, per_page: int = 20):
        """Lista paginada de petições sem número."""
        return (
            SavedPetition.query.filter_by(user_id=user_id)
            .filter(
                (SavedPetition.process_number.is_(None))
                | (SavedPetition.process_number == "")
            )
            .filter(SavedPetition.status == "completed")
            .order_by(SavedPetition.completed_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )


class ClientRepository:
    """Repositório para clientes no contexto de processos."""

    @staticmethod
    def get_choices(lawyer_id: int) -> List[Tuple[str, str]]:
        """Retorna lista de clientes para select."""
        clients = (
            Client.query.filter_by(lawyer_id=lawyer_id)
            .order_by(Client.full_name)
            .all()
        )
        choices = [("", "Nenhum cliente vinculado")]
        choices.extend([(str(c.id), c.full_name) for c in clients])
        return choices
