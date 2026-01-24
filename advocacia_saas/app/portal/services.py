"""
Services para o Portal do Cliente
Camada de lógica de negócio
"""

import logging
import os
import traceback
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from flask import url_for
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from app import db
from app.portal.repository import PortalRepository

# Logger específico para o portal
portal_logger = logging.getLogger("portal")


class PortalAuthService:
    """Serviço de autenticação do portal"""

    @staticmethod
    def validate_login(email: str, password: str) -> tuple[bool, str, Any]:
        """
        Valida credenciais de login do cliente
        
        Returns:
            tuple: (success, message, user)
        """
        user = PortalRepository.get_user_by_email(email)

        if not user:
            portal_logger.warning(f"Email não encontrado: {email}")
            return False, "Email não encontrado.", None

        if not check_password_hash(user.password_hash, password):
            portal_logger.warning(f"Senha incorreta para email: {email}")
            return False, "Senha incorreta.", None

        # Verificar se é cliente
        client = PortalRepository.get_client_by_user_id(user.id)
        if not client:
            portal_logger.warning(f"Usuário {email} não é cliente, acesso negado")
            return False, "Acesso negado. Este portal é exclusivo para clientes.", None

        portal_logger.info(f"Login bem-sucedido para cliente: {email} (ID: {user.id})")
        return True, "Login bem-sucedido", user

    @staticmethod
    def validate_next_url(next_url: str) -> bool:
        """
        Valida URL de redirecionamento para prevenir Open Redirect
        
        Returns:
            bool: True se URL é segura (relativa)
        """
        if not next_url:
            return False
        parsed = urlparse(next_url)
        # Só permite URLs relativas (sem domínio externo)
        is_safe = not parsed.netloc and not parsed.scheme
        if not is_safe:
            portal_logger.warning(f"Tentativa de Open Redirect bloqueada: {next_url}")
        return is_safe


class PortalDashboardService:
    """Serviço para dashboard do portal"""

    @staticmethod
    def get_dashboard_data(user_id: int) -> dict[str, Any]:
        """
        Obtém dados do dashboard do cliente
        
        Returns:
            dict com estatísticas e dados do dashboard
        """
        client = PortalRepository.get_client_by_user_id_or_404(user_id)

        data = {
            "client": client,
            "total_documents": PortalRepository.count_client_documents(client.id),
            "pending_deadlines": PortalRepository.count_pending_deadlines(client.id),
            "upcoming_deadlines": PortalRepository.get_upcoming_deadlines(client.id, 5),
            "unread_messages": PortalRepository.count_unread_messages(user_id),
            "recent_documents": PortalRepository.get_recent_documents(client.id, 5),
        }

        portal_logger.info(
            f"Dashboard carregado: {data['total_documents']} docs, "
            f"{data['pending_deadlines']} prazos, {data['unread_messages']} mensagens"
        )

        return data


class PortalDocumentService:
    """Serviço de documentos do portal"""

    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "gif"}

    @staticmethod
    def get_client_documents(user_id: int) -> tuple[Any, list]:
        """Lista documentos do cliente"""
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        documents = PortalRepository.get_client_documents(client.id)
        portal_logger.info(f"{len(documents)} documentos encontrados para cliente {client.id}")
        return client, documents

    @staticmethod
    def upload_document(
        user_id: int,
        file,
        title: str | None = None,
        document_type: str = "outros",
    ) -> tuple[bool, str, Any]:
        """
        Faz upload de documento
        
        Returns:
            tuple: (success, message, document)
        """
        try:
            client = PortalRepository.get_client_by_user_id_or_404(user_id)

            if not file or file.filename == "":
                return False, "Nenhum arquivo selecionado", None

            original_filename = secure_filename(file.filename)
            file_ext = os.path.splitext(original_filename)[1].lower()

            # Gerar nome único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"cliente_{client.id}_{timestamp}{file_ext}"

            portal_logger.debug(f"Arquivo: {original_filename} -> {unique_filename}")

            # Salvar arquivo
            upload_dir = PortalRepository.get_upload_directory(client.id)
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)

            file_size = os.path.getsize(file_path)
            portal_logger.debug(f"Arquivo salvo: {file_path}, tamanho: {file_size} bytes")

            # Criar documento no banco
            document = PortalRepository.create_document(
                user_id=user_id,
                client_id=client.id,
                title=title or original_filename,
                document_type=document_type,
                filename=original_filename,
                file_path=file_path,
                file_type=file.content_type,
                file_size=file_size,
            )

            portal_logger.info(f"Upload bem-sucedido: {original_filename} para cliente {client.id}")
            return True, "Arquivo enviado com sucesso!", document

        except Exception as e:
            portal_logger.error(f"Erro no upload: {str(e)}")
            portal_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False, "Erro ao fazer upload do arquivo. Tente novamente.", None

    @staticmethod
    def get_document_for_download(user_id: int, document_id: int) -> tuple[Any, str, str]:
        """
        Obtém documento para download
        
        Returns:
            tuple: (document, base_path, stored_filename)
        """
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        document = PortalRepository.get_document_by_id_and_client(document_id, client.id)
        base_path, stored_filename = PortalRepository.get_absolute_file_path(document.file_path)
        return document, base_path, stored_filename


class PortalChatService:
    """Serviço de chat do portal"""

    @staticmethod
    def get_chat_data(user_id: int) -> tuple[Any, list, bool]:
        """
        Obtém dados do chat
        
        Returns:
            tuple: (client, messages, has_chat_room)
        """
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        has_chat_room = client.lawyer_id is not None
        messages = []

        if has_chat_room:
            messages = PortalRepository.get_chat_messages(
                user_id, client.lawyer_id, client.id
            )

        portal_logger.debug(f"{len(messages)} mensagens encontradas para cliente {client.id}")
        return client, messages, has_chat_room

    @staticmethod
    def get_messages_as_dict(user_id: int) -> list[dict]:
        """Lista mensagens formatadas como dicionário"""
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        messages = PortalRepository.get_chat_messages(user_id, client.lawyer_id, client.id)

        messages_data = []
        for message in messages:
            if message.sender_id == user_id:
                sender_type = "client"
            elif message.message_type == "bot":
                sender_type = "bot"
            else:
                sender_type = "lawyer"

            messages_data.append({
                "id": message.id,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read,
                "sender_type": sender_type,
                "message_type": message.message_type,
            })

        return messages_data

    @staticmethod
    def send_message(
        user_id: int,
        content: str,
        use_bot: bool = True,
    ) -> tuple[bool, str, dict]:
        """
        Envia mensagem no chat
        
        Returns:
            tuple: (success, message, response_data)
        """
        try:
            from app.services.chatbot_service import ChatBotService

            content = content.strip()
            if not content:
                return False, "Mensagem não pode ser vazia", {}

            client = PortalRepository.get_client_by_user_id_or_404(user_id)

            # Criar mensagem do cliente
            client_message = PortalRepository.create_message(
                sender_id=user_id,
                recipient_id=client.lawyer_id,
                client_id=client.id,
                content=content,
                message_type="text",
                is_read=False,
            )

            portal_logger.info(f"Mensagem enviada: ID {client_message.id} de cliente {client.id}")

            response_data = {
                "message": {
                    "id": client_message.id,
                    "content": client_message.content,
                    "created_at": client_message.created_at.isoformat(),
                    "is_read": client_message.is_read,
                    "sender_type": "client",
                },
            }

            # Processar com bot se habilitado
            if use_bot:
                bot = ChatBotService(client)
                bot_response, bot_data = bot.process_message(content)
                bot_message = bot.create_bot_message(bot_response)
                db.session.commit()

                response_data["bot_response"] = {
                    "id": bot_message.id,
                    "content": bot_message.content,
                    "created_at": bot_message.created_at.isoformat(),
                    "is_read": True,
                    "sender_type": "bot",
                    "data": bot_data,
                }

                portal_logger.info(f"Bot respondeu mensagem {client_message.id}")

            return True, "Mensagem enviada", response_data

        except Exception as e:
            portal_logger.error(f"Erro ao enviar mensagem: {str(e)}")
            portal_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False, str(e), {}

    @staticmethod
    def clear_chat(user_id: int) -> tuple[bool, str, int]:
        """
        Limpa histórico do chat
        
        Returns:
            tuple: (success, message, deleted_count)
        """
        try:
            client = PortalRepository.get_client_by_user_id_or_404(user_id)
            deleted_count = PortalRepository.delete_client_messages(user_id, client.id)
            return True, f"Chat limpo. {deleted_count} mensagens removidas.", deleted_count
        except Exception as e:
            return False, str(e), 0


class PortalTimelineService:
    """Serviço de timeline do portal"""

    @staticmethod
    def get_timeline_events(user_id: int) -> list[dict]:
        """Obtém eventos da timeline do cliente"""
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        processes = PortalRepository.get_client_processes(client.id)

        timeline_events = []

        for process in processes:
            # Movimentações
            movements = PortalRepository.get_process_movements(process.id)
            for movement in movements:
                timeline_events.append({
                    "id": f"movement_{movement.id}",
                    "type": "movement",
                    "title": movement.description,
                    "date": movement.created_at,
                    "process_title": process.title,
                    "status": "completed",
                    "category": "judicial",
                })

            # Custos
            costs = PortalRepository.get_process_costs(process.id)
            for cost in costs:
                timeline_events.append({
                    "id": f"cost_{cost.id}",
                    "type": "cost",
                    "title": f"Custo: R$ {cost.amount:.2f}",
                    "date": cost.created_at,
                    "process_title": process.title,
                    "status": "completed",
                    "category": "financial",
                })

        # Ordenar por data decrescente
        timeline_events.sort(key=lambda x: x["date"], reverse=True)
        return timeline_events


class PortalCalendarService:
    """Serviço de calendário do portal"""

    @staticmethod
    def get_calendar_events(user_id: int) -> list[dict]:
        """Obtém eventos do calendário do cliente"""
        client = PortalRepository.get_client_by_user_id_or_404(user_id)
        events = []

        # Prazos
        deadlines = PortalRepository.get_client_deadlines(client.id)
        for deadline in deadlines:
            is_overdue = deadline.is_overdue()
            is_pending = deadline.status == "pending"

            if is_overdue:
                color = "#dc3545"
            elif is_pending:
                color = "#ffc107"
            else:
                color = "#28a745"

            events.append({
                "id": f"deadline_{deadline.id}",
                "title": deadline.title,
                "start": deadline.deadline_date.isoformat(),
                "description": deadline.description,
                "status": deadline.status,
                "type": "deadline",
                "backgroundColor": color,
                "borderColor": color,
                "urgent": is_overdue,
            })

        # Eventos de calendário
        calendar_events = PortalRepository.get_client_calendar_events(client.id)
        event_colors = {
            "audiencia": "#dc3545",
            "reuniao": "#007bff",
            "prazo": "#ffc107",
            "compromisso": "#28a745",
        }

        for event in calendar_events:
            if event.status == "requested":
                event_color = "#fd7e14"
                title = f"⏳ {event.title.replace('Solicitação: ', '')}"
            else:
                event_color = event_colors.get(event.event_type, "#6c757d")
                title = event.title

            events.append({
                "id": f"event_{event.id}",
                "title": title,
                "start": event.start_datetime.isoformat(),
                "end": event.end_datetime.isoformat(),
                "description": event.description,
                "location": event.location,
                "virtual_link": event.virtual_link,
                "status": event.status,
                "type": "meeting",
                "event_type": event.event_type,
                "backgroundColor": event_color,
                "borderColor": event_color,
                "allDay": event.all_day,
            })

        return events

    @staticmethod
    def schedule_meeting(
        user_id: int,
        title: str,
        description: str,
        preferred_date: str,
        preferred_time: str,
        duration: int = 60,
        meeting_type: str = "reuniao",
        process_id: int | None = None,
    ) -> tuple[bool, str]:
        """
        Agenda solicitação de reunião
        
        Returns:
            tuple: (success, message)
        """
        try:
            if not title or not preferred_date or not preferred_time:
                return False, "Preencha todos os campos obrigatórios."

            client = PortalRepository.get_client_by_user_id_or_404(user_id)

            # Combinar data e hora
            start_datetime = datetime.strptime(
                f"{preferred_date} {preferred_time}", "%Y-%m-%d %H:%M"
            )
            end_datetime = start_datetime + timedelta(minutes=int(duration))

            # Criar evento
            description_with_client = f"Solicitado por {client.full_name}: {description}"
            PortalRepository.create_meeting_request(
                user_id=user_id,
                client_id=client.id,
                title=title,
                description=description_with_client,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                event_type=meeting_type,
                process_id=process_id if process_id else None,
            )

            # Notificar advogado
            lawyer = client.get_primary_lawyer()
            if lawyer:
                notification_msg = (
                    f"Cliente {client.full_name} solicitou agendamento: "
                    f"{title} para {start_datetime.strftime('%d/%m/%Y %H:%M')}"
                )
                PortalRepository.create_notification(
                    user_id=lawyer.id,
                    notification_type="meeting_request",
                    title="Nova solicitação de reunião",
                    message=notification_msg,
                    link=url_for("advanced.calendar"),
                )

            portal_logger.info(f"Cliente {client.full_name} solicitou reunião: {title}")
            return True, "Solicitação enviada com sucesso!"

        except Exception as e:
            portal_logger.error(f"Erro ao solicitar reunião: {str(e)}")
            return False, "Erro ao enviar solicitação. Tente novamente."


class PortalLogsService:
    """Serviço para visualização de logs"""

    @staticmethod
    def get_log_content() -> tuple[list[str], str]:
        """
        Lê conteúdo do arquivo de log
        
        Returns:
            tuple: (log_lines, log_file_path)
        """
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "logs",
            "portal.log",
        )

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs_content = f.read()
            portal_logger.debug(f"Log lido: {len(logs_content)} caracteres")
            log_lines = logs_content.split("\n") if logs_content else []
        else:
            portal_logger.warning(f"Arquivo de log não encontrado: {log_file}")
            log_lines = ["Arquivo de log não encontrado."]

        return log_lines, log_file
