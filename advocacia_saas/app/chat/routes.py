"""
Rotas HTTP do sistema de chat
"""

import os
from datetime import datetime

from flask import (
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.chat import bp
from app.models import ChatRoom, Client, Message


@bp.route("/")
@login_required
def index():
    """Página principal do chat - lista de conversas"""
    # Buscar todas as salas de chat do usuário
    if current_user.user_type == "lawyer" or current_user.user_type == "master":
        chat_rooms = (
            ChatRoom.query.filter_by(lawyer_id=current_user.id)
            .order_by(ChatRoom.last_message_at.desc().nullslast())
            .all()
        )
    else:
        # Para clientes (se tiverem acesso)
        chat_rooms = []

    return render_template("chat/index.html", chat_rooms=chat_rooms)


@bp.route("/room/<int:room_id>")
@login_required
def room(room_id):
    """Sala de chat específica"""
    chat_room = ChatRoom.query.get_or_404(room_id)

    # Verificar permissão
    if current_user.id != chat_room.lawyer_id:
        abort(403)

    # Buscar mensagens
    messages = (
        Message.query.filter(
            db.or_(
                db.and_(
                    Message.sender_id == current_user.id,
                    Message.recipient_id == chat_room.client.user_id,
                ),
                db.and_(
                    Message.sender_id == chat_room.client.user_id,
                    Message.recipient_id == current_user.id,
                ),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    # Marcar mensagens como lidas
    chat_room.mark_as_read_by(current_user.id)
    for msg in messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.mark_as_read()

    return render_template(
        "chat/room.html",
        chat_room=chat_room,
        messages=messages,
        client=chat_room.client,
    )


@bp.route("/start/<int:client_id>", methods=["GET", "POST"])
@login_required
def start_chat(client_id):
    """Inicia novo chat com cliente"""
    client = Client.query.get_or_404(client_id)

    # Verificar se já existe sala de chat
    chat_room = ChatRoom.query.filter_by(
        lawyer_id=current_user.id, client_id=client_id
    ).first()

    if not chat_room:
        # Criar nova sala
        chat_room = ChatRoom(
            lawyer_id=current_user.id,
            client_id=client_id,
            title=f"Chat com {client.name}",
        )
        db.session.add(chat_room)
        db.session.commit()

        # Mensagem de sistema
        system_msg = Message(
            sender_id=current_user.id,
            recipient_id=client.user_id if client.user_id else current_user.id,
            client_id=client_id,
            content=f"Chat iniciado com {client.name}",
            message_type="system",
        )
        db.session.add(system_msg)
        db.session.commit()

    return redirect(url_for("chat.room", room_id=chat_room.id))


@bp.route("/api/send", methods=["POST"])
@login_required
def send_message():
    """API para enviar mensagem"""
    data = request.get_json()

    recipient_id = data.get("recipient_id")
    content = data.get("content")
    client_id = data.get("client_id")

    if not recipient_id or not content:
        return jsonify({"error": "Dados incompletos"}), 400

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
    chat_room = ChatRoom.query.filter_by(
        lawyer_id=current_user.id, client_id=client_id
    ).first()

    if chat_room:
        chat_room.update_last_message(message)

    return jsonify({"success": True, "message": message.to_dict()})


@bp.route("/api/messages/<int:room_id>")
@login_required
def get_messages(room_id):
    """API para buscar mensagens de uma sala"""
    chat_room = ChatRoom.query.get_or_404(room_id)

    # Verificar permissão
    if current_user.id != chat_room.lawyer_id:
        return jsonify({"error": "Sem permissão"}), 403

    # Buscar mensagens
    messages = (
        Message.query.filter(
            db.or_(
                db.and_(
                    Message.sender_id == current_user.id,
                    Message.recipient_id == chat_room.client.user_id,
                ),
                db.and_(
                    Message.sender_id == chat_room.client.user_id,
                    Message.recipient_id == current_user.id,
                ),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    return jsonify({"messages": [msg.to_dict() for msg in messages]})


@bp.route("/api/mark-read/<int:message_id>", methods=["POST"])
@login_required
def mark_read(message_id):
    """Marca mensagem como lida"""
    message = Message.query.get_or_404(message_id)

    if message.recipient_id != current_user.id:
        return jsonify({"error": "Sem permissão"}), 403

    message.mark_as_read()

    return jsonify({"success": True})


@bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """Upload de arquivo no chat"""
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    recipient_id = request.form.get("recipient_id")
    client_id = request.form.get("client_id")

    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if not recipient_id:
        return jsonify({"error": "Destinatário não especificado"}), 400

    # Salvar arquivo
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{filename}"

    upload_folder = os.path.join(current_app.root_path, "static", "uploads", "chat")
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Criar mensagem
    file_size = os.path.getsize(filepath)
    message = Message(
        sender_id=current_user.id,
        recipient_id=int(recipient_id),
        client_id=int(client_id) if client_id else None,
        content=f"Arquivo enviado: {file.filename}",
        message_type="file",
        attachment_filename=file.filename,
        attachment_path=f"uploads/chat/{filename}",
        attachment_size=file_size,
        attachment_type=file.content_type,
    )
    db.session.add(message)
    db.session.commit()

    # Atualizar chat room
    if client_id:
        chat_room = ChatRoom.query.filter_by(
            lawyer_id=current_user.id, client_id=int(client_id)
        ).first()

        if chat_room:
            chat_room.update_last_message(message)

    return jsonify({"success": True, "message": message.to_dict()})


@bp.route("/download/<int:message_id>")
@login_required
def download_file(message_id):
    """Download de arquivo anexado"""
    message = Message.query.get_or_404(message_id)

    # Verificar permissão
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        abort(403)

    if not message.attachment_path:
        abort(404)

    # Extrair diretório e arquivo
    directory = os.path.dirname(
        os.path.join(current_app.root_path, "static", message.attachment_path)
    )
    filename = os.path.basename(message.attachment_path)

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=message.attachment_filename,
    )


@bp.route("/api/rooms")
@login_required
def get_rooms():
    """API para listar salas de chat"""
    if current_user.user_type == "lawyer" or current_user.user_type == "master":
        chat_rooms = (
            ChatRoom.query.filter_by(lawyer_id=current_user.id)
            .order_by(ChatRoom.last_message_at.desc().nullslast())
            .all()
        )
    else:
        chat_rooms = []

    return jsonify({"rooms": [room.to_dict() for room in chat_rooms]})


@bp.route("/api/unread-count")
@login_required
def unread_count():
    """API para contar mensagens não lidas"""
    count = Message.query.filter_by(recipient_id=current_user.id, is_read=False).count()

    return jsonify({"count": count})
