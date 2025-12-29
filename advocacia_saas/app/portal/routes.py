"""
Rotas do Portal do Cliente
"""

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
    jsonify,
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import logging
import traceback

from app import db
from app.models import ChatRoom, Client, Deadline, Document, Message, User, Process, ProcessMovement, ProcessCost
from app.portal import bp

# Configurar logging específico para o portal
portal_logger = logging.getLogger('portal')
portal_logger.setLevel(logging.DEBUG)

# Criar handler para arquivo
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'portal.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)

# Criar formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
file_handler.setFormatter(formatter)

# Adicionar handler ao logger
if not portal_logger.handlers:
    portal_logger.addHandler(file_handler)


def client_required(f):
    """Decorator para verificar se usuário é cliente"""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Redirecionar para login do portal com next parameter
            return redirect(url_for("portal.login", next=request.url))

        # Verificar se é cliente
        client = Client.query.filter_by(user_id=current_user.id).first()
        if not client:
            flash("Acesso negado. Este portal é exclusivo para clientes.", "danger")
            logout_user()
            return redirect(url_for("portal.login"))

        return f(*args, **kwargs)

    return decorated_function


@bp.route("/")
@client_required
def index():
    """Dashboard do portal do cliente"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando dashboard do portal")

        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        portal_logger.debug(f"Cliente encontrado: {client.id} - {client.full_name}")

        # Estatísticas
        total_documents = Document.query.filter_by(client_id=client.id).count()
        pending_deadlines = Deadline.query.filter_by(
            client_id=client.id, status="pending"
        ).count()

        # Próximos prazos
        upcoming_deadlines = (
            Deadline.query.filter_by(client_id=client.id, status="pending")
            .order_by(Deadline.deadline_date.asc())
            .limit(5)
            .all()
        )

        # Mensagens não lidas
        unread_messages = Message.query.filter_by(
            recipient_id=current_user.id, is_read=False
        ).count()

        # Atividades recentes
        recent_documents = (
            Document.query.filter_by(client_id=client.id)
            .order_by(Document.created_at.desc())
            .limit(5)
            .all()
        )

        portal_logger.info(f"Dashboard carregado com sucesso para {current_user.email}: {total_documents} docs, {pending_deadlines} prazos, {unread_messages} mensagens")

        return render_template(
            "portal/index.html",
            client=client,
            total_documents=total_documents,
            pending_deadlines=pending_deadlines,
            upcoming_deadlines=upcoming_deadlines,
            unread_messages=unread_messages,
            recent_documents=recent_documents,
        )

    except Exception as e:
        portal_logger.error(f"Erro no dashboard do portal para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro ao carregar o dashboard. Tente novamente.", "danger")
        return redirect(url_for("portal.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login do cliente"""
    try:
        if current_user.is_authenticated:
            portal_logger.info(f"Usuário já autenticado {current_user.email} redirecionado para dashboard")
            return redirect(url_for("portal.index"))

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            portal_logger.info(f"Tentativa de login para email: {email}")

            user = User.query.filter_by(email=email).first()

            if not user:
                portal_logger.warning(f"Email não encontrado: {email}")
                flash("Email não encontrado.", "danger")
                return redirect(url_for("portal.login"))

            if not check_password_hash(user.password_hash, password):
                portal_logger.warning(f"Senha incorreta para email: {email}")
                flash("Senha incorreta.", "danger")
                return redirect(url_for("portal.login"))

            # Verificar se é cliente
            client = Client.query.filter_by(user_id=user.id).first()
            if not client:
                portal_logger.warning(f"Usuário {email} não é cliente, acesso negado")
                flash("Acesso negado. Este portal é exclusivo para clientes.", "danger")
                return redirect(url_for("portal.login"))

            login_user(user)
            portal_logger.info(f"Login bem-sucedido para cliente: {email} (ID: {user.id})")
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("portal.index"))

        portal_logger.debug("Página de login do portal acessada")
        return render_template("portal/login.html")

    except Exception as e:
        portal_logger.error(f"Erro na rota de login do portal: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro interno do servidor. Tente novamente.", "danger")
        return redirect(url_for("portal.login"))


@bp.route("/logout")
@login_required
def logout():
    """Logout do cliente"""
    logout_user()
    return redirect(url_for("portal.login"))


@bp.route("/documents")
@client_required
def documents():
    """Lista de documentos do cliente"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando lista de documentos")

        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        portal_logger.debug(f"Cliente encontrado: {client.id}")

        documents = Document.query.filter_by(client_id=client.id).order_by(
            Document.created_at.desc()
        ).all()

        portal_logger.info(f"{len(documents)} documentos encontrados para cliente {client.id}")

        return render_template("portal/documents.html", documents=documents)

    except Exception as e:
        portal_logger.error(f"Erro ao carregar documentos para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro ao carregar documentos. Tente novamente.", "danger")
        return redirect(url_for("portal.index"))


@bp.route("/upload", methods=["GET", "POST"])
@client_required
def upload():
    """Upload de documentos"""
    try:
        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        portal_logger.info(f"Usuário {current_user.email} acessando upload de documentos")

        if request.method == "POST":
            portal_logger.debug(f"Iniciando upload para cliente {client.id}")

            if "file" not in request.files:
                portal_logger.warning(f"Nenhum arquivo selecionado no upload para {current_user.email}")
                flash("Nenhum arquivo selecionado", "danger")
                return redirect(request.url)

            file = request.files["file"]
            if file.filename == "":
                portal_logger.warning(f"Nome de arquivo vazio no upload para {current_user.email}")
                flash("Nenhum arquivo selecionado", "danger")
                return redirect(request.url)

            if file:
                filename = secure_filename(file.filename)
                portal_logger.debug(f"Arquivo seguro: {filename}, tipo: {file.content_type}")

                # Criar diretório se não existir
                upload_dir = os.path.join("uploads", "portal", str(client.id))
                os.makedirs(upload_dir, exist_ok=True)
                portal_logger.debug(f"Diretório de upload criado/verificado: {upload_dir}")

                # Salvar arquivo
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)

                # Verificar tamanho do arquivo
                file_size = os.path.getsize(file_path)
                portal_logger.debug(f"Arquivo salvo: {file_path}, tamanho: {file_size} bytes")

                # Salvar no banco
                document = Document(
                    client_id=client.id,
                    filename=filename,
                    file_path=file_path,
                    file_type=file.content_type,
                    file_size=file_size,
                )
                db.session.add(document)
                db.session.commit()

                portal_logger.info(f"Upload bem-sucedido: {filename} para cliente {client.id}")
                flash("Arquivo enviado com sucesso!", "success")
                return redirect(url_for("portal.documents"))

        portal_logger.debug(f"Página de upload acessada por {current_user.email}")
        return render_template("portal/upload.html")

    except Exception as e:
        portal_logger.error(f"Erro no upload para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        flash("Erro ao fazer upload do arquivo. Tente novamente.", "danger")
        return redirect(url_for("portal.upload"))


@bp.route("/download/<int:document_id>")
@client_required
def download_document(document_id):
    """Download de documento"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    document = Document.query.filter_by(
        id=document_id, client_id=client.id
    ).first_or_404()

    return send_from_directory(
        os.path.dirname(document.file_path),
        os.path.basename(document.file_path),
        as_attachment=True,
    )


@bp.route("/calendar")
@client_required
def calendar():
    """Calendário de prazos"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    return render_template("portal/calendar.html", client=client)


@bp.route("/api/calendar/events")
@client_required
def get_calendar_events():
    """API para eventos do calendário"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    deadlines = Deadline.query.filter_by(client_id=client.id).all()

    events = []
    for deadline in deadlines:
        events.append({
            "id": deadline.id,
            "title": deadline.title,
            "start": deadline.deadline_date.isoformat(),
            "description": deadline.description,
            "status": deadline.status,
            "backgroundColor": "#dc3545" if deadline.status == "overdue" else "#ffc107" if deadline.status == "pending" else "#28a745",
            "borderColor": "#dc3545" if deadline.status == "overdue" else "#ffc107" if deadline.status == "pending" else "#28a745",
        })

    return jsonify(events)


@bp.route("/timeline")
@client_required
def timeline():
    """Timeline visual do processo"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Buscar processos do cliente
    processes = Process.query.filter_by(client_id=client.id).order_by(Process.created_at.desc()).all()

    # Preparar dados para timeline
    timeline_events = []

    for process in processes:
        # Movimentações do processo
        movements = ProcessMovement.query.filter_by(process_id=process.id).order_by(ProcessMovement.created_at.asc()).all()

        for movement in movements:
            timeline_events.append({
                "id": f"movement_{movement.id}",
                "type": "movement",
                "title": movement.description,
                "date": movement.created_at,
                "process_title": process.title,
                "status": "completed",
                "category": "judicial"
            })

        # Custos do processo
        costs = ProcessCost.query.filter_by(process_id=process.id).order_by(ProcessCost.created_at.asc()).all()

        for cost in costs:
            timeline_events.append({
                "id": f"cost_{cost.id}",
                "type": "cost",
                "title": f"Custo: R$ {cost.amount:.2f}",
                "date": cost.created_at,
                "process_title": process.title,
                "status": "completed",
                "category": "financial"
            })

    # Ordenar por data
    timeline_events.sort(key=lambda x: x["date"], reverse=True)

    return render_template("portal/timeline.html", timeline_events=timeline_events)


@bp.route("/chat")
@client_required
def chat():
    """Chat com o advogado"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando chat")

        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        portal_logger.debug(f"Cliente encontrado para chat: {client.id}")

        # Buscar ou criar sala de chat
        chat_room = ChatRoom.query.filter_by(client_id=client.id).first()
        if not chat_room:
            portal_logger.info(f"Criando nova sala de chat para cliente {client.id}")
            chat_room = ChatRoom(client_id=client.id)
            db.session.add(chat_room)
            db.session.commit()
        else:
            portal_logger.debug(f"Sala de chat existente encontrada: {chat_room.id}")

        # Buscar mensagens
        messages = Message.query.filter_by(chat_room_id=chat_room.id).order_by(Message.created_at.asc()).all()
        portal_logger.debug(f"{len(messages)} mensagens encontradas na sala {chat_room.id}")

        return render_template("portal/chat.html", messages=messages)

    except Exception as e:
        portal_logger.error(f"Erro ao carregar chat para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro ao carregar o chat. Tente novamente.", "danger")
        return redirect(url_for("portal.index"))


@bp.route("/api/chat/messages")
@client_required
def get_chat_messages():
    """API para buscar mensagens do chat"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()
    chat_room = ChatRoom.query.filter_by(client_id=client.id).first()

    if not chat_room:
        return jsonify([])

    messages = Message.query.filter_by(chat_room_id=chat_room.id).order_by(Message.created_at.asc()).all()

    messages_data = []
    for message in messages:
        messages_data.append({
            "id": message.id,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
            "is_read": message.is_read,
            "sender_type": message.sender_type,
        })

    return jsonify(messages_data)


@bp.route("/api/chat/send", methods=["POST"])
@client_required
def send_chat_message():
    """API para enviar mensagem no chat"""
    try:
        portal_logger.debug(f"Enviando mensagem no chat para {current_user.email}")

        data = request.get_json()
        content = data.get("content", "").strip()
        message_type = data.get("message_type", "text")

        portal_logger.debug(f"Conteúdo da mensagem: '{content[:50]}...', tipo: {message_type}")

        if not content:
            portal_logger.warning(f"Mensagem vazia rejeitada para {current_user.email}")
            return jsonify({"error": "Conteúdo da mensagem é obrigatório"}), 400

        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        chat_room = ChatRoom.query.filter_by(client_id=client.id).first()

        if not chat_room:
            portal_logger.info(f"Criando sala de chat para cliente {client.id} durante envio de mensagem")
            chat_room = ChatRoom(client_id=client.id)
            db.session.add(chat_room)
            db.session.commit()

        message = Message(
            chat_room_id=chat_room.id,
            sender_id=current_user.id,
            sender_type="client",
            content=content,
            message_type=message_type,
            is_read=False
        )

        db.session.add(message)
        db.session.commit()

        portal_logger.info(f"Mensagem enviada com sucesso: ID {message.id} para sala {chat_room.id}")

        return jsonify({
            "success": True,
            "message": {
                "id": message.id,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "is_read": message.is_read
            }
        })

    except Exception as e:
        portal_logger.error(f"Erro ao enviar mensagem no chat para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/api/chat/clear", methods=["POST"])
@client_required
def clear_chat():
    """Limpar histórico do chat"""
    try:
        client = Client.query.filter_by(user_id=current_user.id).first_or_404()
        chat_room = ChatRoom.query.filter_by(client_id=client.id).first()

        if not chat_room:
            return jsonify({"error": "Chat não encontrado"}), 404

        # Deletar todas as mensagens do chat
        Message.query.filter_by(chat_room_id=chat_room.id).delete()
        db.session.commit()

        return jsonify({"success": True, "message": "Chat limpo com sucesso"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/api/push/vapid-key")
@client_required
def get_vapid_key():
    """Retornar chave VAPID pública para push notifications"""
    from app.config import Config
    import base64

    vapid_private_key = Config.VAPID_PRIVATE_KEY
    vapid_public_key = Config.VAPID_PUBLIC_KEY

    if not vapid_public_key:
        return jsonify({"error": "VAPID keys not configured"}), 500

    return jsonify({"publicKey": vapid_public_key})


@bp.route("/api/push/subscribe", methods=["POST"])
@client_required
def subscribe_push():
    """Inscrever para push notifications"""
    try:
        data = request.get_json()
        subscription = data.get("subscription")

        if not subscription:
            return jsonify({"error": "Subscription data required"}), 400

        client = Client.query.filter_by(user_id=current_user.id).first_or_404()

        # Aqui você pode salvar a subscription no banco se quiser
        # Por enquanto, apenas confirmamos o sucesso

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/profile")
@client_required
def profile():
    """Perfil do cliente"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    return render_template("portal/profile.html", client=client)


@bp.route("/logs")
@client_required
def view_logs():
    """Visualizar logs do portal (apenas para debug)"""
    try:
        portal_logger.info(f"Usuário {current_user.email} acessando visualização de logs")

        log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'portal.log')

        logs_content = ""
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs_content = f.read()
            portal_logger.debug(f"Arquivo de log lido com sucesso: {len(logs_content)} caracteres")
        else:
            portal_logger.warning(f"Arquivo de log não encontrado: {log_file}")
            logs_content = "Arquivo de log não encontrado."

        # Separar logs por linhas para exibição
        log_lines = logs_content.split('\n') if logs_content else []

        return render_template("portal/logs.html", log_lines=log_lines, log_file=log_file)

    except Exception as e:
        portal_logger.error(f"Erro ao visualizar logs para {current_user.email}: {str(e)}")
        portal_logger.error(f"Traceback: {traceback.format_exc()}")
        flash("Erro ao carregar os logs.", "danger")
        return redirect(url_for("portal.index"))