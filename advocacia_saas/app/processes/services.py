"""
Processes Services - Camada de Lógica de Negócio.

Serviços para gestão de processos judiciais.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app import db
from app.processes.notifications import get_unread_notifications
from app.processes.repository import (
    ClientRepository,
    PetitionRepository,
    ProcessRepository,
)
from app.models import Deadline, Process, User
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

        # Sincronizar deadline se data informada
        if next_deadline:
            cls._sync_process_deadline(
                process=process,
                deadline_date=next_deadline,
                description=deadline_description,
                user_id=user_id,
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

        # Sincronizar deadline se data informada ou alterada
        next_deadline = kwargs.get("next_deadline")
        deadline_description = kwargs.get("deadline_description")
        if next_deadline is not None:
            cls._sync_process_deadline(
                process=process,
                deadline_date=next_deadline if next_deadline else None,
                description=deadline_description,
                user_id=process.user_id,
            )

        return ProcessResult(success=True, process=process)

    @classmethod
    def delete_process(cls, process: Process) -> str:
        """
        Remove processo.

        Returns:
            Título do processo removido.
        """
        title = process.title
        
        # Remover deadlines vinculados ao processo
        Deadline.query.filter_by(process_id=process.id).delete()
        
        ProcessRepository.delete(process)
        return title

    @classmethod
    def _sync_process_deadline(
        cls,
        process: Process,
        deadline_date,
        description: Optional[str],
        user_id: int,
    ) -> Optional[Deadline]:
        """
        Sincroniza o próximo prazo do processo com o calendário de deadlines.
        
        - Se já existe um deadline pendente para este processo, atualiza
        - Se não existe, cria um novo
        - Se deadline_date é None, marca o deadline existente como cancelado
        
        Args:
            process: Processo a sincronizar
            deadline_date: Data do prazo (date ou datetime)
            description: Descrição do prazo
            user_id: ID do usuário
            
        Returns:
            Deadline criado/atualizado ou None
        """
        # Buscar deadline existente para este processo (pendente)
        existing_deadline = Deadline.query.filter_by(
            process_id=process.id,
            status="pending"
        ).first()
        
        # Se não tem data, cancelar deadline existente
        if not deadline_date:
            if existing_deadline:
                existing_deadline.status = "canceled"
                existing_deadline.updated_at = datetime.now(timezone.utc)
                db.session.commit()
            return None
        
        # Converter date para datetime se necessário
        if hasattr(deadline_date, 'hour'):
            deadline_datetime = deadline_date
        else:
            deadline_datetime = datetime.combine(
                deadline_date, 
                datetime.min.time()
            ).replace(tzinfo=timezone.utc)
        
        # Obter configuração de alerta do usuário
        user = User.query.get(user_id)
        alert_days = user.deadline_alert_days if user else 10
        
        # Título do deadline
        deadline_title = f"Prazo: {process.title}"
        if description:
            deadline_title = f"{description} - {process.title}"
        
        if existing_deadline:
            # Atualizar deadline existente
            existing_deadline.deadline_date = deadline_datetime
            existing_deadline.title = deadline_title
            existing_deadline.description = description or f"Prazo processual - Processo: {process.process_number or process.title}"
            existing_deadline.alert_days_before = alert_days
            existing_deadline.alert_sent = False  # Resetar alerta ao mudar data
            existing_deadline.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return existing_deadline
        else:
            # Criar novo deadline
            new_deadline = Deadline(
                user_id=user_id,
                process_id=process.id,
                client_id=process.client_id,
                title=deadline_title,
                description=description or f"Prazo processual - Processo: {process.process_number or process.title}",
                deadline_type="prazo_processual",
                deadline_date=deadline_datetime,
                alert_days_before=alert_days,
                status="pending",
            )
            db.session.add(new_deadline)
            db.session.commit()
            return new_deadline
