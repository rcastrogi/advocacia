"""
Eventos WebSocket do chat usando Flask-SocketIO
"""

from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from app import db, socketio
from app.models import ChatRoom, Message


@socketio.on("connect")
def handle_connect():
    """Cliente conectou ao WebSocket"""
    if current_user.is_authenticated:
        print(f"Cliente conectado: {current_user.name} (ID: {current_user.id})")
        emit("connected", {"message": "Conectado ao chat"})
    else:
        return False  # Rejeitar conexão não autenticada


@socketio.on("disconnect")
def handle_disconnect():
    """Cliente desconectou"""
    if current_user.is_authenticated:
        print(f"Cliente desconectado: {current_user.name}")


@socketio.on("join")
def handle_join(data):
    """Entrar em uma sala de chat"""
    room_id = data.get("room_id")

    if not room_id:
        return

    # Verificar permissão
    chat_room = db.session.get(ChatRoom, room_id)
    if not chat_room or current_user.id != chat_room.lawyer_id:
        return

    room = f"room_{room_id}"
    join_room(room)

    emit(
        "joined",
        {"room_id": room_id, "message": f"{current_user.name} entrou no chat"},
        room=room,
    )


@socketio.on("leave")
def handle_leave(data):
    """Sair de uma sala de chat"""
    room_id = data.get("room_id")

    if not room_id:
        return

    room = f"room_{room_id}"
    leave_room(room)

    emit(
        "left",
        {"room_id": room_id, "message": f"{current_user.name} saiu do chat"},
        room=room,
    )


@socketio.on("send_message")
def handle_send_message(data):
    """Enviar mensagem via WebSocket"""
    room_id = data.get("room_id")
    content = data.get("content")
    recipient_id = data.get("recipient_id")
    client_id = data.get("client_id")

    if not room_id or not content or not recipient_id:
        emit("error", {"message": "Dados incompletos"})
        return

    # Criar mensagem
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        client_id=client_id,
        content=content,
        message_type="text",
    )
    db.session.add(message)
    db.session.commit()

    # Atualizar chat room
    chat_room = db.session.get(ChatRoom, room_id)
    if chat_room:
        chat_room.update_last_message(message)

    # Emitir mensagem para todos na sala
    room = f"room_{room_id}"
    emit("new_message", {"message": message.to_dict(), "room_id": room_id}, room=room)

    # Notificar destinatário se estiver online mas não na sala
    emit(
        "notification",
        {"type": "new_message", "message": message.to_dict(), "room_id": room_id},
        room=f"user_{recipient_id}",
    )


@socketio.on("typing")
def handle_typing(data):
    """Notificar que usuário está digitando"""
    room_id = data.get("room_id")

    if not room_id:
        return

    room = f"room_{room_id}"
    emit(
        "user_typing",
        {
            "user_id": current_user.id,
            "user_name": current_user.name,
            "room_id": room_id,
        },
        room=room,
        include_self=False,
    )


@socketio.on("stop_typing")
def handle_stop_typing(data):
    """Notificar que usuário parou de digitar"""
    room_id = data.get("room_id")

    if not room_id:
        return

    room = f"room_{room_id}"
    emit(
        "user_stop_typing",
        {"user_id": current_user.id, "room_id": room_id},
        room=room,
        include_self=False,
    )


@socketio.on("mark_read")
def handle_mark_read(data):
    """Marcar mensagens como lidas"""
    message_ids = data.get("message_ids", [])

    for msg_id in message_ids:
        message = db.session.get(Message, msg_id)
        if message and message.recipient_id == current_user.id:
            message.mark_as_read()

    emit(
        "messages_read",
        {"message_ids": message_ids, "user_id": current_user.id},
        broadcast=True,
    )


@socketio.on("get_online_users")
def handle_get_online_users():
    """Retornar lista de usuários online"""
    # TODO: Implementar rastreamento de usuários online
    # Por enquanto, retorna lista vazia
    emit("online_users", {"users": []})
