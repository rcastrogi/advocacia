"""
Repository para o Portal do Cliente
Camada de acesso a dados
"""

import os
from datetime import datetime

from flask import current_app
from sqlalchemy import and_, or_

from app import db
from app.models import (
    CalendarEvent,
    Client,
    Deadline,
    Document,
    Message,
    Notification,
    Process,
    ProcessCost,
    ProcessMovement,
    User,
)


class PortalRepository:
    """Repository para operações de dados do portal"""

    # ==================== CLIENT ====================

    @staticmethod
    def get_client_by_user_id(user_id: int) -> Client | None:
        """Busca cliente pelo ID do usuário"""
        return Client.query.filter_by(user_id=user_id).first()

    @staticmethod
    def get_client_by_user_id_or_404(user_id: int) -> Client:
        """Busca cliente pelo ID do usuário ou 404"""
        return Client.query.filter_by(user_id=user_id).first_or_404()

    # ==================== USER ====================

    @staticmethod
    def get_user_by_email(email: str) -> User | None:
        """Busca usuário pelo email"""
        return User.query.filter_by(email=email).first()

    # ==================== DOCUMENTS ====================

    @staticmethod
    def get_client_documents(client_id: int) -> list[Document]:
        """Lista documentos do cliente ordenados por data"""
        return (
            Document.query.filter_by(client_id=client_id)
            .order_by(Document.created_at.desc())
            .all()
        )

    @staticmethod
    def get_recent_documents(client_id: int, limit: int = 5) -> list[Document]:
        """Lista documentos recentes do cliente"""
        return (
            Document.query.filter_by(client_id=client_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_client_documents(client_id: int) -> int:
        """Conta documentos do cliente"""
        return Document.query.filter_by(client_id=client_id).count()

    @staticmethod
    def get_document_by_id_and_client(document_id: int, client_id: int) -> Document:
        """Busca documento por ID e cliente ou 404"""
        return Document.query.filter_by(
            id=document_id, client_id=client_id
        ).first_or_404()

    @staticmethod
    def create_document(
        user_id: int,
        client_id: int,
        title: str,
        document_type: str,
        filename: str,
        file_path: str,
        file_type: str,
        file_size: int,
    ) -> Document:
        """Cria novo documento"""
        document = Document(
            user_id=user_id,
            client_id=client_id,
            title=title,
            document_type=document_type,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
        )
        db.session.add(document)
        db.session.commit()
        return document

    # ==================== DEADLINES ====================

    @staticmethod
    def count_pending_deadlines(client_id: int) -> int:
        """Conta prazos pendentes do cliente"""
        return Deadline.query.filter_by(client_id=client_id, status="pending").count()

    @staticmethod
    def get_upcoming_deadlines(client_id: int, limit: int = 5) -> list[Deadline]:
        """Lista próximos prazos do cliente"""
        return (
            Deadline.query.filter_by(client_id=client_id, status="pending")
            .order_by(Deadline.deadline_date.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_client_deadlines(client_id: int) -> list[Deadline]:
        """Lista todos os prazos do cliente"""
        return Deadline.query.filter_by(client_id=client_id).all()

    # ==================== MESSAGES ====================

    @staticmethod
    def count_unread_messages(user_id: int) -> int:
        """Conta mensagens não lidas"""
        return Message.query.filter_by(recipient_id=user_id, is_read=False).count()

    @staticmethod
    def get_chat_messages(
        user_id: int, lawyer_id: int, client_id: int
    ) -> list[Message]:
        """Busca mensagens do chat entre cliente e advogado"""
        return (
            Message.query.filter(
                or_(
                    and_(
                        Message.sender_id == user_id,
                        Message.recipient_id == lawyer_id,
                    ),
                    and_(
                        Message.sender_id == lawyer_id,
                        Message.recipient_id == user_id,
                    ),
                    and_(
                        Message.client_id == client_id,
                        Message.message_type == "bot",
                    ),
                )
            )
            .order_by(Message.created_at.asc())
            .all()
        )

    @staticmethod
    def create_message(
        sender_id: int,
        recipient_id: int,
        client_id: int,
        content: str,
        message_type: str = "text",
        is_read: bool = False,
    ) -> Message:
        """Cria nova mensagem"""
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            client_id=client_id,
            content=content,
            message_type=message_type,
            is_read=is_read,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def delete_client_messages(user_id: int, client_id: int) -> int:
        """Deleta todas as mensagens do cliente"""
        deleted_count = Message.query.filter(
            or_(
                Message.sender_id == user_id,
                Message.recipient_id == user_id,
                Message.client_id == client_id,
            )
        ).delete(synchronize_session=False)
        db.session.commit()
        return deleted_count

    # ==================== PROCESSES ====================

    @staticmethod
    def get_client_processes(client_id: int) -> list[Process]:
        """Lista processos do cliente"""
        return (
            Process.query.filter_by(client_id=client_id)
            .order_by(Process.created_at.desc())
            .all()
        )

    @staticmethod
    def get_process_movements(process_id: int) -> list[ProcessMovement]:
        """Lista movimentações do processo"""
        return (
            ProcessMovement.query.filter_by(process_id=process_id)
            .order_by(ProcessMovement.created_at.asc())
            .all()
        )

    @staticmethod
    def get_process_costs(process_id: int) -> list[ProcessCost]:
        """Lista custos do processo"""
        return (
            ProcessCost.query.filter_by(process_id=process_id)
            .order_by(ProcessCost.created_at.asc())
            .all()
        )

    # ==================== CALENDAR EVENTS ====================

    @staticmethod
    def get_client_calendar_events(client_id: int) -> list[CalendarEvent]:
        """Lista eventos de calendário do cliente"""
        return CalendarEvent.query.filter(CalendarEvent.client_id == client_id).all()

    @staticmethod
    def count_pending_meeting_requests(client_ids: list[int]) -> int:
        """Conta solicitações de reunião pendentes"""
        if not client_ids:
            return 0
        return CalendarEvent.query.filter(
            CalendarEvent.client_id.in_(client_ids),
            CalendarEvent.status == "requested",
        ).count()

    @staticmethod
    def create_meeting_request(
        user_id: int,
        client_id: int,
        title: str,
        description: str,
        start_datetime: datetime,
        end_datetime: datetime,
        event_type: str,
        process_id: int | None = None,
    ) -> CalendarEvent:
        """Cria solicitação de reunião"""
        event = CalendarEvent(
            user_id=user_id,
            title=f"Solicitação: {title}",
            description=f"Solicitado: {description}",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            event_type=event_type,
            client_id=client_id,
            process_id=process_id,
            status="requested",
            priority="normal",
        )
        db.session.add(event)
        db.session.commit()
        return event

    # ==================== NOTIFICATIONS ====================

    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        link: str | None = None,
    ) -> None:
        """Cria notificação"""
        Notification.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )

    # ==================== FILE OPERATIONS ====================

    @staticmethod
    def get_upload_directory(client_id: int) -> str:
        """Retorna diretório de upload do cliente"""
        upload_dir = os.path.join("uploads", "portal", str(client_id))
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @staticmethod
    def get_absolute_file_path(file_path: str) -> tuple[str, str]:
        """Retorna caminho absoluto e nome do arquivo"""
        full_path = os.path.join(current_app.root_path, "..", file_path)
        base_path = os.path.abspath(os.path.dirname(full_path))
        stored_filename = os.path.basename(file_path)
        return base_path, stored_filename
