"""
Chat Repository - Camada de Acesso a Dados.

Operações de banco de dados para o sistema de chat.
"""

import os
from datetime import datetime
from typing import List, Optional

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.models import ChatRoom, Client, Message


class ChatRoomRepository:
    """Repositório para operações com salas de chat."""

    @staticmethod
    def find_by_id(room_id: int) -> Optional[ChatRoom]:
        """Busca sala de chat pelo ID."""
        return ChatRoom.query.get(room_id)

    @staticmethod
    def find_by_lawyer_and_client(lawyer_id: int, client_id: int) -> Optional[ChatRoom]:
        """Busca sala de chat por advogado e cliente."""
        return ChatRoom.query.filter_by(
            lawyer_id=lawyer_id, client_id=client_id
        ).first()

    @staticmethod
    def get_rooms_by_lawyer(lawyer_id: int) -> List[ChatRoom]:
        """Lista salas de chat de um advogado."""
        return (
            ChatRoom.query.filter_by(lawyer_id=lawyer_id)
            .order_by(ChatRoom.last_message_at.desc().nullslast())
            .all()
        )

    @staticmethod
    def create(lawyer_id: int, client_id: int, title: str) -> ChatRoom:
        """Cria nova sala de chat."""
        chat_room = ChatRoom(
            lawyer_id=lawyer_id,
            client_id=client_id,
            title=title,
        )
        db.session.add(chat_room)
        db.session.commit()
        return chat_room

    @staticmethod
    def update_last_message(chat_room: ChatRoom, message: Message):
        """Atualiza última mensagem da sala."""
        chat_room.update_last_message(message)


class MessageRepository:
    """Repositório para operações com mensagens."""

    @staticmethod
    def find_by_id(message_id: int) -> Optional[Message]:
        """Busca mensagem pelo ID."""
        return Message.query.get(message_id)

    @staticmethod
    def get_messages_between_users(
        user1_id: int, user2_id: int, order_asc: bool = True
    ) -> List[Message]:
        """Busca mensagens entre dois usuários."""
        query = Message.query.filter(
            db.or_(
                db.and_(
                    Message.sender_id == user1_id,
                    Message.recipient_id == user2_id,
                ),
                db.and_(
                    Message.sender_id == user2_id,
                    Message.recipient_id == user1_id,
                ),
            )
        )
        if order_asc:
            query = query.order_by(Message.created_at.asc())
        else:
            query = query.order_by(Message.created_at.desc())
        return query.all()

    @staticmethod
    def create(
        sender_id: int,
        recipient_id: int,
        content: str,
        client_id: Optional[int] = None,
        message_type: str = "text",
        attachment_filename: Optional[str] = None,
        attachment_path: Optional[str] = None,
        attachment_size: Optional[int] = None,
        attachment_type: Optional[str] = None,
    ) -> Message:
        """Cria nova mensagem."""
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            client_id=client_id,
            content=content,
            message_type=message_type,
            attachment_filename=attachment_filename,
            attachment_path=attachment_path,
            attachment_size=attachment_size,
            attachment_type=attachment_type,
        )
        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def count_unread(user_id: int) -> int:
        """Conta mensagens não lidas de um usuário."""
        return Message.query.filter_by(
            recipient_id=user_id, is_read=False
        ).count()

    @staticmethod
    def mark_as_read(message: Message):
        """Marca mensagem como lida."""
        message.mark_as_read()


class ClientRepository:
    """Repositório para operações com clientes no contexto do chat."""

    @staticmethod
    def find_by_id(client_id: int) -> Optional[Client]:
        """Busca cliente pelo ID."""
        return Client.query.get(client_id)
