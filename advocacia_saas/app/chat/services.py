"""
Chat Services - Camada de Lógica de Negócio.

Serviços para o sistema de chat.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from flask import current_app
from werkzeug.utils import secure_filename

from app.chat.repository import (
    ChatRoomRepository,
    ClientRepository,
    MessageRepository,
)
from app.models import ChatRoom, Client, Message


@dataclass
class ChatRoomInfo:
    """Informações de uma sala de chat."""

    room: ChatRoom
    messages: List[Message]
    client: Client


class ChatService:
    """Serviço principal de chat."""

    @classmethod
    def get_user_rooms(cls, user_id: int, user_type: str) -> List[ChatRoom]:
        """
        Lista salas de chat do usuário.

        Args:
            user_id: ID do usuário
            user_type: Tipo do usuário (lawyer, master, etc.)

        Returns:
            Lista de salas de chat
        """
        if user_type in ("lawyer", "master"):
            return ChatRoomRepository.get_rooms_by_lawyer(user_id)
        return []

    @classmethod
    def get_room_details(
        cls, room_id: int, user_id: int
    ) -> Tuple[Optional[ChatRoomInfo], Optional[str]]:
        """
        Obtém detalhes de uma sala de chat.

        Returns:
            Tupla (ChatRoomInfo, error_message)
        """
        chat_room = ChatRoomRepository.find_by_id(room_id)
        if not chat_room:
            return None, "Sala não encontrada"

        # Verificar permissão
        if user_id != chat_room.lawyer_id:
            return None, "Sem permissão"

        # Buscar mensagens
        client_user_id = chat_room.client.user_id if chat_room.client else None
        if client_user_id:
            messages = MessageRepository.get_messages_between_users(
                user_id, client_user_id
            )
        else:
            messages = []

        return ChatRoomInfo(
            room=chat_room,
            messages=messages,
            client=chat_room.client,
        ), None

    @classmethod
    def start_chat(cls, lawyer_id: int, client_id: int) -> Tuple[ChatRoom, bool]:
        """
        Inicia chat com cliente (cria sala se não existir).

        Returns:
            Tupla (ChatRoom, is_new)
        """
        # Verificar se já existe
        chat_room = ChatRoomRepository.find_by_lawyer_and_client(lawyer_id, client_id)
        if chat_room:
            return chat_room, False

        # Buscar cliente
        client = ClientRepository.find_by_id(client_id)
        if not client:
            raise ValueError("Cliente não encontrado")

        # Criar sala
        chat_room = ChatRoomRepository.create(
            lawyer_id=lawyer_id,
            client_id=client_id,
            title=f"Chat com {client.full_name}",
        )

        # Mensagem de sistema
        recipient_id = client.user_id if client.user_id else lawyer_id
        MessageRepository.create(
            sender_id=lawyer_id,
            recipient_id=recipient_id,
            client_id=client_id,
            content=f"Chat iniciado com {client.full_name}",
            message_type="system",
        )

        return chat_room, True

    @classmethod
    def mark_room_as_read(
        cls, chat_room: ChatRoom, user_id: int, messages: List[Message]
    ):
        """Marca sala e mensagens como lidas."""
        chat_room.mark_as_read_by(user_id)
        for msg in messages:
            if msg.recipient_id == user_id and not msg.is_read:
                msg.mark_as_read()


class MessageService:
    """Serviço de mensagens."""

    @classmethod
    def send_message(
        cls,
        sender_id: int,
        recipient_id: int,
        content: str,
        client_id: Optional[int] = None,
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Envia uma mensagem.

        Returns:
            Tupla (Message, error_message)
        """
        if not recipient_id or not content:
            return None, "Dados incompletos"

        message = MessageRepository.create(
            sender_id=sender_id,
            recipient_id=recipient_id,
            client_id=client_id,
            content=content,
            message_type="text",
        )

        # Atualizar chat room
        if client_id:
            chat_room = ChatRoomRepository.find_by_lawyer_and_client(
                sender_id, client_id
            )
            if chat_room:
                ChatRoomRepository.update_last_message(chat_room, message)

        return message, None

    @classmethod
    def get_room_messages(
        cls, room_id: int, user_id: int
    ) -> Tuple[Optional[List[Message]], Optional[str]]:
        """
        Busca mensagens de uma sala.

        Returns:
            Tupla (messages, error_message)
        """
        chat_room = ChatRoomRepository.find_by_id(room_id)
        if not chat_room:
            return None, "Sala não encontrada"

        if user_id != chat_room.lawyer_id:
            return None, "Sem permissão"

        client_user_id = chat_room.client.user_id if chat_room.client else None
        if client_user_id:
            messages = MessageRepository.get_messages_between_users(
                user_id, client_user_id
            )
        else:
            messages = []

        return messages, None

    @classmethod
    def mark_message_read(
        cls, message_id: int, user_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Marca mensagem como lida.

        Returns:
            Tupla (success, error_message)
        """
        message = MessageRepository.find_by_id(message_id)
        if not message:
            return False, "Mensagem não encontrada"

        if message.recipient_id != user_id:
            return False, "Sem permissão"

        message.mark_as_read()
        return True, None

    @classmethod
    def get_unread_count(cls, user_id: int) -> int:
        """Retorna contagem de mensagens não lidas."""
        return MessageRepository.count_unread(user_id)


class FileUploadService:
    """Serviço de upload de arquivos no chat."""

    UPLOAD_FOLDER = "uploads/chat"

    @classmethod
    def upload_file(
        cls,
        file,
        sender_id: int,
        recipient_id: int,
        client_id: Optional[int] = None,
    ) -> Tuple[Optional[Message], Optional[str]]:
        """
        Faz upload de arquivo no chat.

        Returns:
            Tupla (Message, error_message)
        """
        if not file or file.filename == "":
            return None, "Nenhum arquivo selecionado"

        if not recipient_id:
            return None, "Destinatário não especificado"

        # Salvar arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"

        upload_folder = os.path.join(current_app.root_path, "static", cls.UPLOAD_FOLDER)
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        file_size = os.path.getsize(filepath)

        # Criar mensagem
        message = MessageRepository.create(
            sender_id=sender_id,
            recipient_id=recipient_id,
            client_id=client_id,
            content=f"Arquivo enviado: {file.filename}",
            message_type="file",
            attachment_filename=file.filename,
            attachment_path=f"{cls.UPLOAD_FOLDER}/{unique_filename}",
            attachment_size=file_size,
            attachment_type=file.content_type,
        )

        # Atualizar chat room
        if client_id:
            chat_room = ChatRoomRepository.find_by_lawyer_and_client(
                sender_id, client_id
            )
            if chat_room:
                ChatRoomRepository.update_last_message(chat_room, message)

        return message, None

    @classmethod
    def get_file_path(
        cls, message_id: int, user_id: int
    ) -> Tuple[Optional[Tuple[str, str, str]], Optional[str]]:
        """
        Obtém caminho do arquivo para download.

        Returns:
            Tupla ((directory, filename, download_name), error_message)
        """
        message = MessageRepository.find_by_id(message_id)
        if not message:
            return None, "Mensagem não encontrada"

        if message.sender_id != user_id and message.recipient_id != user_id:
            return None, "Sem permissão"

        if not message.attachment_path:
            return None, "Arquivo não encontrado"

        directory = os.path.dirname(
            os.path.join(current_app.root_path, "static", message.attachment_path)
        )
        filename = os.path.basename(message.attachment_path)

        return (directory, filename, message.attachment_filename), None
