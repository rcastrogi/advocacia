"""
Rotas do Portal do Cliente
"""

import logging
import os
import traceback
from functools import wraps

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app import db, limiter
from app.decorators import validate_with_schema
from app.models import Client, Process
from app.portal import bp
from app.portal.services import (
    PortalAuthService,
    PortalCalendarService,
    PortalChatService,
    PortalDashboardService,
    PortalDocumentService,
    PortalLogsService,
    PortalTimelineService,
)
from app.portal.repository import PortalRepository
from app.schemas import ChatMessageSchema, PushSubscriptionSchema, UserPreferencesSchema

# Logger
portal_logger = logging.getLogger("portal")

# Configurar handler se não existir
if not portal_logger.handlers:
    log_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs",
        "portal.log",
    )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(formatter)
    portal_logger.addHandler(file_handler)
    portal_logger.setLevel(logging.DEBUG)


def client_required(f):
    """Decorator para verificar se usuário é cliente"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("portal.login", next=request.url))

        client = PortalRepository.get_client_by_user_id(current_user.id)
        if not client:
            flash("Acesso negado. Este portal é exclusivo para clientes.", "danger")
            logout_user()
            return redirect(url_for("portal.login"))

        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# AUTENTICAÇÃO
# =============================================================================


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login do cliente"""
    try:
        if current_user.is_authenticated:
            portal_logger.info(f"Usuário já autenticado {current_user.email} redirecionado")
            return redirect(url_for("portal.index"))

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            portal_logger.info(f"Tentativa de login para email: {email}")

            success, message, user = PortalAuthService.validate_login(email, password)

            if not success:
                flash(message, "danger")
                return redirect(url_for("portal.login"))

            login_user(user)

            next_page = request.args.get("next")
            if next_page and PortalAuthService.validate_next_url(next_page):
                return redirect(next_page)

            return redirect(url_for("portal.index"))

        return render_template("portal/login.html")

    except Exception as e:
        portal_logger.error(f"Erro na rota de login: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro interno do servidor. Tente novamente.", "danger")
        return redirect(url_for("portal.login"))


@bp.route("/logout")
@login_required
def logout():
    """Logout do cliente"""
    logout_user()
    return redirect(url_for("portal.login"))


# =============================================================================
# DASHBOARD
# =============================================================================


@bp.route("/")
@client_required
def index():
    """Dashboard do portal do cliente"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando dashboard")

        data = PortalDashboardService.get_dashboard_data(current_user.id)

        return render_template("portal/index.html", **data)

    except Exception as e:
        portal_logger.error(f"Erro no dashboard: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro ao carregar o dashboard. Tente novamente.", "danger")
        return redirect(url_for("portal.login"))


# =============================================================================
# DOCUMENTOS
# =============================================================================


@bp.route("/documents")
@client_required
def documents():
    """Lista de documentos do cliente"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando documentos")

        client, docs = PortalDocumentService.get_client_documents(current_user.id)

        return render_template("portal/documents.html", documents=docs)

    except Exception as e:
        portal_logger.error(f"Erro ao carregar documentos: {str(e)}")
        flash("Erro ao carregar documentos. Tente novamente.", "danger")
        return redirect(url_for("portal.index"))


@bp.route("/upload", methods=["GET", "POST"])
@client_required
def upload():
    """Upload de documentos"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando upload")

        if request.method == "POST":
            file = request.files.get("file")
            title = request.form.get("title")
            document_type = request.form.get("document_type", "outros")

            success, message, document = PortalDocumentService.upload_document(
                user_id=current_user.id,
                file=file,
                title=title,
                document_type=document_type,
            )

            flash(message, "success" if success else "danger")
            if success:
                return redirect(url_for("portal.documents"))
            return redirect(request.url)

        return render_template("portal/upload.html")

    except Exception as e:
        portal_logger.error(f"Erro no upload: {str(e)}")
        flash("Erro ao fazer upload do arquivo.", "danger")
        return redirect(url_for("portal.upload"))


@bp.route("/download/<int:document_id>")
@client_required
def download_document(document_id):
    """Download ou visualização de documento"""
    document, base_path, stored_filename = PortalDocumentService.get_document_for_download(
        current_user.id, document_id
    )

    as_attachment = request.args.get("download") == "1"

    return send_from_directory(
        base_path,
        stored_filename,
        as_attachment=as_attachment,
        download_name=document.filename if as_attachment else None,
    )


# =============================================================================
# CALENDÁRIO
# =============================================================================


@bp.route("/calendar")
@client_required
def calendar():
    """Calendário de prazos"""
    client = PortalRepository.get_client_by_user_id_or_404(current_user.id)
    return render_template("portal/calendar.html", client=client)


@bp.route("/api/calendar/events")
@client_required
def get_calendar_events():
    """API para eventos do calendário"""
    events = PortalCalendarService.get_calendar_events(current_user.id)
    return jsonify(events)


@bp.route("/schedule-meeting", methods=["GET", "POST"])
@client_required
def schedule_meeting():
    """Página para solicitar agendamento de reunião"""
    client = PortalRepository.get_client_by_user_id_or_404(current_user.id)

    if request.method == "POST":
        success, message = PortalCalendarService.schedule_meeting(
            user_id=current_user.id,
            title=request.form.get("title"),
            description=request.form.get("description", ""),
            preferred_date=request.form.get("preferred_date"),
            preferred_time=request.form.get("preferred_time"),
            duration=int(request.form.get("duration", 60)),
            meeting_type=request.form.get("meeting_type", "reuniao"),
            process_id=request.form.get("process_id"),
        )

        flash(message, "success" if success else "warning")
        if success:
            return redirect(url_for("portal.calendar"))
        return redirect(request.url)

    processes = Process.query.filter_by(client_id=client.id).all()
    return render_template("portal/schedule_meeting.html", client=client, processes=processes)


# =============================================================================
# TIMELINE
# =============================================================================


@bp.route("/timeline")
@client_required
def timeline():
    """Timeline visual do processo"""
    timeline_events = PortalTimelineService.get_timeline_events(current_user.id)
    return render_template("portal/timeline.html", timeline_events=timeline_events)


# =============================================================================
# CHAT
# =============================================================================


@bp.route("/chat")
@client_required
def chat():
    """Chat com o advogado"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando chat")

        client, messages, chat_room = PortalChatService.get_chat_data(current_user.id)

        return render_template(
            "portal/chat.html",
            messages=messages,
            client=client,
            chat_room=chat_room,
        )

    except Exception as e:
        portal_logger.error(f"Erro ao carregar chat: {str(e)}")
        flash("Erro ao carregar o chat. Tente novamente.", "danger")
        return redirect(url_for("portal.index"))


@bp.route("/api/chat/messages")
@client_required
def get_chat_messages():
    """API para buscar mensagens do chat"""
    messages_data = PortalChatService.get_messages_as_dict(current_user.id)
    return jsonify(messages_data)


@bp.route("/api/chat/send", methods=["POST"])
@client_required
@limiter.limit("20 per minute")
@validate_with_schema(ChatMessageSchema, location="json")
def send_chat_message():
    """API para enviar mensagem no chat"""
    data = request.validated_data
    content = (data.get("message") or data.get("content", "")).strip()
    use_bot = data.get("use_bot", True)

    success, message, response_data = PortalChatService.send_message(
        user_id=current_user.id,
        content=content,
        use_bot=use_bot,
    )

    if not success:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({"success": True, **response_data})


@bp.route("/api/chat/clear", methods=["POST"])
@client_required
@limiter.limit("5 per hour")
def clear_chat():
    """Limpar histórico do chat"""
    success, message, deleted_count = PortalChatService.clear_chat(current_user.id)

    if not success:
        return jsonify({"error": message}), 500

    return jsonify({"success": True, "message": message})


# =============================================================================
# PERFIL E OUTROS
# =============================================================================


@bp.route("/profile")
@client_required
def profile():
    """Perfil do cliente"""
    client = PortalRepository.get_client_by_user_id_or_404(current_user.id)
    return render_template("portal/profile.html", client=client)


@bp.route("/help")
@client_required
def help():
    """Página de ajuda"""
    client = PortalRepository.get_client_by_user_id(current_user.id)
    return render_template("portal/help.html", client=client)


@bp.route("/logs")
@client_required
def view_logs():
    """Visualizar logs do portal (debug)"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando logs")

        log_lines, log_file = PortalLogsService.get_log_content()

        return render_template("portal/logs.html", log_lines=log_lines, log_file=log_file)

    except Exception as e:
        portal_logger.error(f"Erro ao visualizar logs: {str(e)}")
        flash("Erro ao carregar os logs.", "danger")
        return redirect(url_for("portal.index"))


# =============================================================================
# PUSH NOTIFICATIONS
# =============================================================================


@bp.route("/api/push/vapid-key")
@client_required
def get_vapid_key():
    """Retornar chave VAPID pública para push notifications"""
    from app.config import Config

    vapid_public_key = Config.VAPID_PUBLIC_KEY

    if not vapid_public_key:
        return jsonify({"error": "VAPID keys not configured"}), 500

    return jsonify({"publicKey": vapid_public_key})


@bp.route("/api/push/subscribe", methods=["POST"])
@client_required
@limiter.limit("5 per minute")
@validate_with_schema(PushSubscriptionSchema, location="json")
def subscribe_push():
    """Inscrever para push notifications"""
    try:
        data = request.validated_data
        # Aqui você pode salvar a subscription no banco se quiser
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
