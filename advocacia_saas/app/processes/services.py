"""
Processes Services - Camada de Lógica de Negócio.

Serviços para gestão de processos judiciais.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.processes.notifications import get_unread_notifications
from app.processes.repository import (
    ClientRepository,
    PetitionRepository,
    ProcessRepository,
)
from app.models import Process
from app.utils.pagination import PaginationHelper


@dataclass
class DashboardStats:
    """Estatísticas do dashboard de processos."""

    total_processes: int
    pending_processes: int
    ongoing_processes: int
    petitions_without_number: int
    urgent_deadlines: int


@dataclass
class ProcessResult:
    """Resultado de operação com processo."""

    success: bool
    process: Optional[Process] = None
    error_message: Optional[str] = None


class ProcessService:
    """Serviço principal de processos."""

    @classmethod
    def get_dashboard_data(cls, user_id: int) -> Dict[str, Any]:
        """
        Obtém dados para o dashboard de processos.

        Returns:
            Dicionário com stats, processos recentes, etc.
        """
        # Estatísticas
        stats = DashboardStats(
            total_processes=ProcessRepository.count_by_user(user_id),
            pending_processes=ProcessRepository.count_by_status(
                user_id, "pending_distribution"
            ),
            ongoing_processes=ProcessRepository.count_by_status(user_id, "ongoing"),
            petitions_without_number=len(
                PetitionRepository.get_without_process_number(user_id)
            ),
            urgent_deadlines=ProcessRepository.get_with_urgent_deadlines(user_id),
        )

        return {
            "stats": {
                "total_processes": stats.total_processes,
                "pending_processes": stats.pending_processes,
                "ongoing_processes": stats.ongoing_processes,
                "petitions_without_number": stats.petitions_without_number,
            },
            "recent_processes": ProcessRepository.get_recent(user_id),
            "petitions_without_number": PetitionRepository.get_without_process_number(
                user_id
            ),
            "urgent_deadlines": stats.urgent_deadlines,
            "unread_notifications": get_unread_notifications(user_id, limit=10),
            "processes_by_status": ProcessRepository.get_grouped_by_status(user_id),
        }

    @classmethod
    def list_processes(
        cls,
        user_id: int,
        status: Optional[str] = None,
        search: Optional[str] = None,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Lista processos com filtros e paginação.

        Returns:
            Dicionário com processos paginados e filtros.
        """
        query = ProcessRepository.search(user_id, status=status, search_term=search)

        pagination = PaginationHelper(
            query=query,
            per_page=per_page,
            filters={"status": status, "search": search},
        )

        return {
            "processes": pagination.paginated,
            "pagination": pagination.to_dict(),
            "status_filter": status,
            "search": search,
        }

    @classmethod
    def get_pending_petitions(cls, user_id: int, page: int = 1, per_page: int = 20):
        """Lista petições pendentes de número de processo."""
        return PetitionRepository.get_paginated_without_number(user_id, page, per_page)

    @classmethod
    def get_client_choices(cls, lawyer_id: int) -> List[Tuple[str, str]]:
        """Retorna opções de clientes para formulário."""
        return ClientRepository.get_choices(lawyer_id)

    @classmethod
    def create_process(
        cls,
        user_id: int,
        title: str,
        process_number: Optional[str] = None,
        plaintiff: Optional[str] = None,
        defendant: Optional[str] = None,
        client_id: Optional[int] = None,
        court: Optional[str] = None,
        court_instance: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        district: Optional[str] = None,
        judge: Optional[str] = None,
        status: str = "pending_distribution",
        distribution_date=None,
        next_deadline=None,
        deadline_description: Optional[str] = None,
        priority: str = "normal",
    ) -> ProcessResult:
        """
        Cria novo processo.

        Returns:
            ProcessResult com sucesso ou erro.
        """
        # Verificar duplicidade de número
        if process_number:
            existing = ProcessRepository.find_by_number(process_number)
            if existing:
                return ProcessResult(
                    success=False,
                    error_message="Este número de processo já está cadastrado.",
                )

        process = ProcessRepository.create(
            user_id=user_id,
            process_number=process_number or None,
            title=title,
            plaintiff=plaintiff or None,
            defendant=defendant or None,
            client_id=client_id or None,
            court=court or None,
            court_instance=court_instance or None,
            jurisdiction=jurisdiction or None,
            district=district or None,
            judge=judge or None,
            status=status,
            distribution_date=distribution_date,
            next_deadline=next_deadline,
            deadline_description=deadline_description or None,
            priority=priority,
        )

        return ProcessResult(success=True, process=process)

    @classmethod
    def get_process(cls, process_id: int, user_id: int) -> Optional[Process]:
        """Busca processo verificando permissão."""
        return ProcessRepository.find_by_id_and_user(process_id, user_id)

    @classmethod
    def update_process(
        cls,
        process: Process,
        title: str,
        process_number: Optional[str] = None,
        **kwargs,
    ) -> ProcessResult:
        """
        Atualiza processo existente.

        Returns:
            ProcessResult com sucesso ou erro.
        """
        # Verificar duplicidade se número mudou
        if process_number and process_number != process.process_number:
            existing = ProcessRepository.find_by_number(process_number)
            if existing:
                return ProcessResult(
                    success=False,
                    error_message="Este número de processo já está cadastrado.",
                )

        # Atualizar
        kwargs["process_number"] = process_number or None
        kwargs["title"] = title
        kwargs["updated_at"] = datetime.now(timezone.utc)

        ProcessRepository.update(process, **kwargs)

        return ProcessResult(success=True, process=process)

    @classmethod
    def delete_process(cls, process: Process) -> str:
        """
        Remove processo.

        Returns:
            Título do processo removido.
        """
        title = process.title
        ProcessRepository.delete(process)
        return title
