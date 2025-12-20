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
)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import ChatRoom, Client, Deadline, Document, Message, User
from app.portal import bp


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
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

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

    return render_template(
        "portal/index.html",
        client=client,
        total_documents=total_documents,
        pending_deadlines=pending_deadlines,
        upcoming_deadlines=upcoming_deadlines,
        unread_messages=unread_messages,
        recent_documents=recent_documents,
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login do cliente"""
    if current_user.is_authenticated:
        return redirect(url_for("portal.index"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        print(f"[DEBUG] Tentativa de login: {email}")

        user = User.query.filter_by(email=email).first()

        if not user:
            print(f"[DEBUG] Usuário não encontrado: {email}")
            flash("Email ou senha incorretos", "danger")
        elif not check_password_hash(user.password_hash, password):
            print(f"[DEBUG] Senha incorreta para: {email}")
            flash("Email ou senha incorretos", "danger")
        else:
            print(f"[DEBUG] Senha correta! Verificando se é cliente...")
            # Verificar se é cliente
            client = Client.query.filter_by(user_id=user.id).first()
            if client:
                print(f"[DEBUG] Cliente encontrado! ID: {client.id}")
                login_user(user, remember=True)
                next_page = request.args.get("next")
                print(
                    f"[DEBUG] Redirecionando para: {next_page or url_for('portal.index')}"
                )
                return redirect(next_page or url_for("portal.index"))
            else:
                print(f"[DEBUG] Usuário não é cliente!")
                flash(
                    "Acesso não autorizado. Este login é apenas para clientes.",
                    "danger",
                )

    return render_template("portal/login.html")


@bp.route("/logout")
def logout():
    """Logout do cliente"""
    logout_user()
    return redirect(url_for("portal.login"))


@bp.route("/documents")
@client_required
def documents():
    """Lista de documentos do cliente"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Filtros
    doc_type = request.args.get("type")
    search = request.args.get("search")

    query = Document.query.filter_by(client_id=client.id)

    if doc_type:
        query = query.filter_by(document_type=doc_type)

    if search:
        query = query.filter(Document.title.ilike(f"%{search}%"))

    documents = query.order_by(Document.created_at.desc()).all()

    return render_template(
        "portal/documents.html",
        client=client,
        documents=documents,
        doc_type=doc_type,
        search=search,
    )


@bp.route("/document/<int:doc_id>")
@client_required
def view_document(doc_id):
    """Visualizar documento específico"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()
    document = Document.query.filter_by(id=doc_id, client_id=client.id).first_or_404()

    return render_template(
        "portal/document_view.html", client=client, document=document
    )


@bp.route("/download/<int:doc_id>")
@client_required
def download_document(doc_id):
    """Download de documento"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()
    document = Document.query.filter_by(id=doc_id, client_id=client.id).first_or_404()

    if not document.file_path:
        abort(404)

    import os

    from flask import current_app

    directory = os.path.dirname(
        os.path.join(current_app.root_path, "static", document.file_path)
    )
    filename = os.path.basename(document.file_path)

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=document.filename or filename,
    )


@bp.route("/deadlines")
@client_required
def deadlines():
    """Lista de prazos do cliente"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Filtros
    status = request.args.get("status", "pending")

    query = Deadline.query.filter_by(client_id=client.id)

    if status:
        query = query.filter_by(status=status)

    deadlines_list = query.order_by(Deadline.deadline_date.asc()).all()

    return render_template(
        "portal/deadlines.html", client=client, deadlines=deadlines_list, status=status
    )


@bp.route("/chat")
@client_required
def chat():
    """Chat com advogado"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Buscar sala de chat
    chat_room = ChatRoom.query.filter_by(client_id=client.id).first()

    if not chat_room:
        flash("Ainda não há um chat iniciado com seu advogado.", "info")
        return render_template(
            "portal/chat.html", client=client, chat_room=None, messages=[]
        )

    # Buscar mensagens
    messages = (
        Message.query.filter(
            db.or_(
                db.and_(
                    Message.sender_id == current_user.id,
                    Message.recipient_id == chat_room.lawyer_id,
                ),
                db.and_(
                    Message.sender_id == chat_room.lawyer_id,
                    Message.recipient_id == current_user.id,
                ),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )

    # Marcar como lidas
    chat_room.mark_as_read_by(current_user.id)
    for msg in messages:
        if msg.recipient_id == current_user.id and not msg.is_read:
            msg.mark_as_read()

    return render_template(
        "portal/chat.html", client=client, chat_room=chat_room, messages=messages
    )


@bp.route("/timeline")
@client_required
def timeline():
    """Timeline de atualizações do processo"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Combinar diferentes tipos de eventos
    events = []

    # Documentos
    for doc in (
        Document.query.filter_by(client_id=client.id)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    ):
        events.append(
            {
                "type": "document",
                "title": f"Documento adicionado: {doc.title}",
                "description": doc.description,
                "date": doc.created_at,
                "icon": "fa-file-alt",
                "color": "primary",
            }
        )

    # Prazos cumpridos
    for deadline in (
        Deadline.query.filter_by(client_id=client.id, status="completed")
        .order_by(Deadline.completed_at.desc())
        .limit(10)
        .all()
    ):
        events.append(
            {
                "type": "deadline",
                "title": f"Prazo cumprido: {deadline.title}",
                "description": deadline.completion_notes,
                "date": deadline.completed_at,
                "icon": "fa-check-circle",
                "color": "success",
            }
        )

    # Ordenar por data
    events.sort(key=lambda x: x["date"], reverse=True)

    return render_template("portal/timeline.html", client=client, events=events)


@bp.route("/profile", methods=["GET", "POST"])
@client_required
def profile():
    """Perfil do cliente"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    if request.method == "POST":
        # Atualizar informações básicas
        client.phone = request.form.get("phone")
        client.address = request.form.get("address")

        # Atualizar email do usuário
        current_user.email = request.form.get("email")

        # Atualizar senha se fornecida
        new_password = request.form.get("new_password")
        if new_password:
            current_user.password = generate_password_hash(new_password)

        db.session.commit()
        flash("Perfil atualizado com sucesso!", "success")
        return redirect(url_for("portal.profile"))

    return render_template("portal/profile.html", client=client)


@bp.route("/help")
@client_required
def help():
    """Central de ajuda"""
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    return render_template("portal/help.html", client=client)
