"""
Documents Routes - Rotas HTTP para documentos.

Controllers delegando para os serviços especializados.
"""

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
from flask_login import current_user, login_required

from app.documents import bp
from app.documents.repository import ClientRepository
from app.documents.services import DocumentSearchService, DocumentService


@bp.route("/")
@login_required
def index():
    """Lista todos os documentos do usuário."""
    data = DocumentService.list_documents(
        user_id=current_user.id,
        client_id=request.args.get("client"),
        doc_type=request.args.get("type"),
        search=request.args.get("search"),
    )

    return render_template("documents/index.html", **data)


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Upload de documento."""
    if request.method == "POST":
        result = DocumentService.upload_document(
            file=request.files.get("file"),
            user_id=current_user.id,
            client_id=request.form.get("client_id"),
            title=request.form.get("title"),
            description=request.form.get("description"),
            document_type=request.form.get("document_type"),
            category=request.form.get("category"),
            tags=request.form.get("tags"),
            is_visible_to_client=request.form.get("is_visible_to_client") == "on",
            is_confidential=request.form.get("is_confidential") == "on",
        )

        if not result.success:
            flash(result.error_message, "danger")
            return redirect(request.url)

        flash(f'Documento "{result.document.title}" enviado com sucesso!', "success")
        return redirect(url_for("documents.view", doc_id=result.document.id))

    # GET - Mostrar formulário
    clients = ClientRepository.get_by_user(current_user.id)
    return render_template("documents/upload.html", clients=clients)


@bp.route("/<int:doc_id>")
@login_required
def view(doc_id):
    """Visualizar documento."""
    document, versions = DocumentService.get_document_with_versions(
        doc_id, current_user.id
    )

    if not document:
        abort(404)

    return render_template("documents/view.html", document=document, versions=versions)


@bp.route("/<int:doc_id>/edit", methods=["GET", "POST"])
@login_required
def edit(doc_id):
    """Editar metadados do documento."""
    document = DocumentService.get_document(doc_id, current_user.id)
    if not document:
        abort(404)

    if request.method == "POST":
        DocumentService.update_document(
            document=document,
            title=request.form.get("title"),
            description=request.form.get("description"),
            document_type=request.form.get("document_type"),
            category=request.form.get("category"),
            tags=request.form.get("tags"),
            is_visible_to_client=request.form.get("is_visible_to_client") == "on",
            is_confidential=request.form.get("is_confidential") == "on",
            notes=request.form.get("notes"),
        )

        flash("Documento atualizado com sucesso!", "success")
        return redirect(url_for("documents.view", doc_id=document.id))

    clients = ClientRepository.get_by_user(current_user.id)
    return render_template("documents/edit.html", document=document, clients=clients)


@bp.route("/<int:doc_id>/download")
@login_required
def download(doc_id):
    """Download de documento."""
    file_info, error = DocumentService.get_download_info(doc_id, current_user.id)

    if error:
        abort(404)

    directory, filename, download_name = file_info
    return send_from_directory(
        directory, filename, as_attachment=True, download_name=download_name
    )


@bp.route("/<int:doc_id>/new-version", methods=["POST"])
@login_required
def new_version(doc_id):
    """Upload de nova versão do documento."""
    document = DocumentService.get_document(doc_id, current_user.id)
    if not document:
        abort(404)

    new_doc, error = DocumentService.create_new_version(
        document, request.files.get("file"), current_user.id
    )

    if error:
        flash(error, "danger")
        return redirect(url_for("documents.view", doc_id=doc_id))

    flash(f"Nova versão criada (v{new_doc.version})!", "success")
    return redirect(url_for("documents.view", doc_id=new_doc.id))


@bp.route("/<int:doc_id>/archive", methods=["POST"])
@login_required
def archive(doc_id):
    """Arquivar documento."""
    document = DocumentService.get_document(doc_id, current_user.id)
    if not document:
        abort(404)

    DocumentService.archive_document(document)
    flash("Documento arquivado com sucesso!", "success")
    return redirect(url_for("documents.index"))


@bp.route("/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete(doc_id):
    """Deletar documento (soft delete)."""
    document = DocumentService.get_document(doc_id, current_user.id)
    if not document:
        abort(404)

    DocumentService.delete_document(document)
    flash("Documento excluído com sucesso!", "success")
    return redirect(url_for("documents.index"))


@bp.route("/client/<int:client_id>")
@login_required
def by_client(client_id):
    """Listar documentos de um cliente específico."""
    client, documents = DocumentService.get_documents_by_client(
        client_id, current_user.id
    )

    if not client:
        abort(404)

    return render_template(
        "documents/by_client.html", client=client, documents=documents
    )


@bp.route("/api/search")
@login_required
def api_search():
    """API para busca de documentos."""
    query = request.args.get("q", "")
    documents = DocumentSearchService.search(current_user.id, query)
    return jsonify({"documents": documents})


@bp.route("/api/stats")
@login_required
def api_stats():
    """API para estatísticas de documentos."""
    stats = DocumentSearchService.get_stats(current_user.id)
    return jsonify(stats)
