"""
Chat Routes - Rotas HTTP do sistema de chat.

Controllers delegando para os serviços especializados.
"""

from flask import (
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app.chat import bp
from app.chat.services import ChatService, FileUploadService, MessageService
from app.decorators import require_feature


@bp.route("/")
@login_required
@require_feature("client_chat")
def index():
    """Página principal do chat - lista de conversas."""
    chat_rooms = ChatService.get_user_rooms(current_user.id, current_user.user_type)
    return render_template("chat/index.html", chat_rooms=chat_rooms)


@bp.route("/room/<int:room_id>")
@login_required
@require_feature("client_chat")
def room(room_id):
    """Sala de chat específica."""
    room_info, error = ChatService.get_room_details(room_id, current_user.id)

    if error:
        abort(403)

    # Marcar mensagens como lidas
    ChatService.mark_room_as_read(
        room_info.room, current_user.id, room_info.messages
    )

    return render_template(
        "chat/room.html",
        chat_room=room_info.room,
        messages=room_info.messages,
        client=room_info.client,
    )


@bp.route("/start/<int:client_id>", methods=["GET", "POST"])
@login_required
def start_chat(client_id):
    """Inicia novo chat com cliente."""
    try:
        chat_room, _ = ChatService.start_chat(current_user.id, client_id)
        return redirect(url_for("chat.room", room_id=chat_room.id))
    except ValueError:
        abort(404)


@bp.route("/api/send", methods=["POST"])
@login_required
def send_message():
    """API para enviar mensagem."""
    data = request.get_json()

    message, error = MessageService.send_message(
        sender_id=current_user.id,
        recipient_id=data.get("recipient_id"),
        content=data.get("content"),
        client_id=data.get("client_id"),
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"success": True, "message": message.to_dict()})


@bp.route("/api/messages/<int:room_id>")
@login_required
def get_messages(room_id):
    """API para buscar mensagens de uma sala."""
    messages, error = MessageService.get_room_messages(room_id, current_user.id)

    if error:
        return jsonify({"error": error}), 403

    return jsonify({"messages": [msg.to_dict() for msg in messages]})


@bp.route("/api/mark-read/<int:message_id>", methods=["POST"])
@login_required
def mark_read(message_id):
    """Marca mensagem como lida."""
    success, error = MessageService.mark_message_read(message_id, current_user.id)

    if not success:
        return jsonify({"error": error}), 403

    return jsonify({"success": True})


@bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    """Upload de arquivo no chat."""
    file = request.files.get("file")
    recipient_id = request.form.get("recipient_id")
    client_id = request.form.get("client_id")

    message, error = FileUploadService.upload_file(
        file=file,
        sender_id=current_user.id,
        recipient_id=int(recipient_id) if recipient_id else None,
        client_id=int(client_id) if client_id else None,
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({"success": True, "message": message.to_dict()})


@bp.route("/download/<int:message_id>")
@login_required
def download_file(message_id):
    """Download de arquivo anexado."""
    file_info, error = FileUploadService.get_file_path(message_id, current_user.id)

    if error:
        abort(403 if "permissão" in error else 404)

    directory, filename, download_name = file_info
    return send_from_directory(
        directory, filename, as_attachment=True, download_name=download_name
    )


@bp.route("/api/rooms")
@login_required
def get_rooms():
    """API para listar salas de chat."""
    chat_rooms = ChatService.get_user_rooms(current_user.id, current_user.user_type)
    return jsonify({"rooms": [room.to_dict() for room in chat_rooms]})


@bp.route("/api/unread-count")
@login_required
def unread_count():
    """API para contar mensagens não lidas."""
    count = MessageService.get_unread_count(current_user.id)
    return jsonify({"count": count})
