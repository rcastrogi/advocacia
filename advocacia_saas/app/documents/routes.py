"""
Rotas de gerenciamento de documentos
"""

import os
from datetime import datetime

from flask import (
    abort,
    current_app,
    flash,
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
from app.documents import bp
from app.models import Client, Document
from app.utils.pagination import PaginationHelper

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "txt",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "zip",
    "rar",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def allowed_file(filename):
    """Verifica se extensão do arquivo é permitida"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/")
@login_required
def index():
    """Lista todos os documentos do usuário"""
    # Filtros
    client_id = request.args.get("client")
    doc_type = request.args.get("type")
    search = request.args.get("search")

    query = Document.query.filter_by(user_id=current_user.id, status="active")

    if client_id:
        query = query.filter_by(client_id=client_id)

    if doc_type:
        query = query.filter_by(document_type=doc_type)

    if search:
        query = query.filter(
            db.or_(
                Document.title.ilike(f"%{search}%"),
                Document.description.ilike(f"%{search}%"),
                Document.tags.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Document.created_at.desc())

    # Paginação
    pagination = PaginationHelper(
        query=query,
        per_page=20,
        filters={"client": client_id, "type": doc_type, "search": search},
    )

    # Buscar clientes para filtro
    clients = (
        Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    )

    return render_template(
        "documents/index.html",
        documents=pagination.items,
        clients=clients,
        selected_client=client_id,
        doc_type=doc_type,
        search=search,
        pagination=pagination.to_dict(),
    )


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Upload de documento"""
    if request.method == "POST":
        # Validar arquivo
        if "file" not in request.files:
            flash("Nenhum arquivo selecionado", "danger")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("Nenhum arquivo selecionado", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Tipo de arquivo não permitido", "danger")
            return redirect(request.url)

        # Dados do formulário
        client_id = request.form.get("client_id")
        title = request.form.get("title")
        description = request.form.get("description")
        document_type = request.form.get("document_type")
        category = request.form.get("category")
        tags = request.form.get("tags")
        is_visible = request.form.get("is_visible_to_client") == "on"
        is_confidential = request.form.get("is_confidential") == "on"

        if not client_id or not title:
            flash("Cliente e título são obrigatórios", "danger")
            return redirect(request.url)

        # Salvar arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"

        upload_folder = os.path.join(
            current_app.root_path, "static", "uploads", "documents"
        )
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        # Informações do arquivo
        file_size = os.path.getsize(filepath)
        file_extension = "." + filename.rsplit(".", 1)[1].lower()

        # Criar documento no banco
        document = Document(
            user_id=current_user.id,
            client_id=client_id,
            title=title,
            description=description,
            document_type=document_type,
            category=category,
            filename=filename,
            file_path=f"uploads/documents/{unique_filename}",
            file_size=file_size,
            file_type=file.content_type,
            file_extension=file_extension,
            tags=tags,
            is_visible_to_client=is_visible,
            is_confidential=is_confidential,
        )

        db.session.add(document)
        db.session.commit()

        flash(f'Documento "{title}" enviado com sucesso!', "success")
        return redirect(url_for("documents.view", doc_id=document.id))

    # GET - Mostrar formulário
    clients = (
        Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    )

    return render_template("documents/upload.html", clients=clients)


@bp.route("/<int:doc_id>")
@login_required
def view(doc_id):
    """Visualizar documento"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()

    # Marcar como acessado
    document.mark_accessed()

    # Buscar versões anteriores
    versions = []
    if document.parent_document_id:
        # Este é uma versão, buscar documento pai e suas versões
        parent = db.session.get(Document, document.parent_document_id)
        if parent:
            versions = (
                Document.query.filter_by(parent_document_id=parent.id)
                .order_by(Document.version.desc())
                .all()
            )
            versions.insert(0, parent)
    else:
        # Este é o documento original, buscar suas versões
        versions = document.versions.order_by(Document.version.desc()).all()

    return render_template("documents/view.html", document=document, versions=versions)


@bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
def edit(doc_id):
    """Editar metadados do documento"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        document.title = request.form.get("title")
        document.description = request.form.get("description")
        document.document_type = request.form.get("document_type")
        document.category = request.form.get("category")
        document.tags = request.form.get("tags")
        document.is_visible_to_client = request.form.get("is_visible_to_client") == "on"
        document.is_confidential = request.form.get("is_confidential") == "on"
        document.notes = request.form.get("notes")

        db.session.commit()

        flash("Documento atualizado com sucesso!", "success")
        return redirect(url_for("documents.view", doc_id=document.id))

    clients = (
        Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    )

    return render_template("documents/edit.html", document=document, clients=clients)


@bp.route("/<int:doc_id>/download")
@login_required
def download(doc_id):
    """Download de documento"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()

    if not document.file_path:
        abort(404)

    # Marcar como acessado
    document.mark_accessed()

    directory = os.path.dirname(
        os.path.join(current_app.root_path, "static", document.file_path)
    )
    filename = os.path.basename(document.file_path)

    return send_from_directory(
        directory, filename, as_attachment=True, download_name=document.filename
    )


@bp.route("/<int:doc_id>/new-version", methods=["POST"])
@login_required
def new_version(doc_id):
    """Upload de nova versão do documento"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()

    if "file" not in request.files:
        flash("Nenhum arquivo selecionado", "danger")
        return redirect(url_for("documents.view", doc_id=doc_id))

    file = request.files["file"]

    if file.filename == "" or not allowed_file(file.filename):
        flash("Arquivo inválido", "danger")
        return redirect(url_for("documents.view", doc_id=doc_id))

    # Salvar arquivo
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{filename}"

    upload_folder = os.path.join(
        current_app.root_path, "static", "uploads", "documents"
    )
    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    file_size = os.path.getsize(filepath)

    # Criar nova versão
    new_doc = document.create_new_version(
        f"uploads/documents/{unique_filename}", filename, file_size, current_user.id
    )

    flash(f"Nova versão criada (v{new_doc.version})!", "success")
    return redirect(url_for("documents.view", doc_id=new_doc.id))


@bp.route("/<int:doc_id>/archive", methods=["POST"])
@login_required
def archive(doc_id):
    """Arquivar documento"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()
    document.archive()

    flash("Documento arquivado com sucesso!", "success")
    return redirect(url_for("documents.index"))


@bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete(doc_id):
    """Deletar documento (soft delete)"""
    document = Document.query.filter_by(
        id=doc_id, user_id=current_user.id
    ).first_or_404()
    document.delete_document()

    flash("Documento excluído com sucesso!", "success")
    return redirect(url_for("documents.index"))


@bp.route("/client/<int:client_id>")
@login_required
def by_client(client_id):
    """Listar documentos de um cliente específico"""
    client = Client.query.filter_by(
        id=client_id, user_id=current_user.id
    ).first_or_404()

    documents = (
        Document.query.filter_by(
            user_id=current_user.id, client_id=client_id, status="active"
        )
        .order_by(Document.created_at.desc())
        .all()
    )

    return render_template(
        "documents/by_client.html", client=client, documents=documents
    )


@bp.route("/api/search")
@login_required
def api_search():
    """API para busca de documentos"""
    query = request.args.get("q", "")

    if len(query) < 2:
        return jsonify({"documents": []})

    documents = (
        Document.query.filter(
            Document.user_id == current_user.id,
            Document.status == "active",
            db.or_(
                Document.title.ilike(f"%{query}%"),
                Document.description.ilike(f"%{query}%"),
                Document.tags.ilike(f"%{query}%"),
            ),
        )
        .limit(10)
        .all()
    )

    return jsonify({"documents": [doc.to_dict() for doc in documents]})


@bp.route("/api/stats")
@login_required
def api_stats():
    """API para estatísticas de documentos"""
    total = Document.query.filter_by(user_id=current_user.id, status="active").count()

    by_type = (
        db.session.query(Document.document_type, db.func.count(Document.id))
        .filter_by(user_id=current_user.id, status="active")
        .group_by(Document.document_type)
        .all()
    )

    total_size = (
        db.session.query(db.func.sum(Document.file_size))
        .filter_by(user_id=current_user.id, status="active")
        .scalar()
        or 0
    )

    return jsonify(
        {
            "total_documents": total,
            "by_type": dict(by_type),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }
    )
