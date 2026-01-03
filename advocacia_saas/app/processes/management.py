"""
Rotas para gestão de andamentos, custos e anexos de processos
"""

import os
from datetime import datetime

from flask import (
    Blueprint,
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
from app.models import Process, ProcessAttachment, ProcessCost, ProcessMovement

bp = Blueprint("process_management", __name__, url_prefix="/processes")

# Configurações para upload
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads",
    "process_attachments",
)
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "txt", "rtf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Criar pasta de upload se não existir
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Verifica se o arquivo tem extensão permitida"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================================
# ANDAMENTOS PROCESSUAIS
# ========================================


@bp.route("/<int:process_id>/movements")
@login_required
def movements(process_id):
    """Lista andamentos de um processo"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    page = request.args.get("page", 1, type=int)
    per_page = 20

    movements_query = ProcessMovement.query.filter_by(process_id=process_id)
    movements_paginated = movements_query.order_by(ProcessMovement.movement_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "processes/movements.html", process=process, movements=movements_paginated
    )


@bp.route("/<int:process_id>/movements/add", methods=["GET", "POST"])
@login_required
def add_movement(process_id):
    """Adiciona novo andamento"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        movement_date = datetime.strptime(request.form["movement_date"], "%Y-%m-%dT%H:%M")
        description = request.form["description"]
        movement_type = request.form.get("movement_type")
        court_decision = request.form.get("court_decision")
        responsible_party = request.form.get("responsible_party")
        internal_notes = request.form.get("internal_notes")
        is_important = "is_important" in request.form
        requires_action = "requires_action" in request.form

        movement = ProcessMovement(
            process_id=process_id,
            movement_date=movement_date,
            description=description,
            movement_type=movement_type,
            court_decision=court_decision,
            responsible_party=responsible_party,
            internal_notes=internal_notes,
            is_important=is_important,
            requires_action=requires_action,
        )

        db.session.add(movement)
        db.session.commit()

        flash("Andamento adicionado com sucesso!", "success")
        return redirect(url_for("process_management.movements", process_id=process_id))

    return render_template("processes/add_movement.html", process=process)


# ========================================
# CUSTOS E HONORÁRIOS
# ========================================


@bp.route("/<int:process_id>/costs")
@login_required
def costs(process_id):
    """Lista custos de um processo"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    costs_query = ProcessCost.query.filter_by(process_id=process_id)
    costs = costs_query.order_by(ProcessCost.created_at.desc()).all()

    # Totais
    total_pending = sum(cost.amount for cost in costs if cost.payment_status == "pending")
    total_paid = sum(cost.amount for cost in costs if cost.payment_status == "paid")

    return render_template(
        "processes/costs.html",
        process=process,
        costs=costs,
        total_pending=total_pending,
        total_paid=total_paid,
    )


@bp.route("/<int:process_id>/costs/add", methods=["GET", "POST"])
@login_required
def add_cost(process_id):
    """Adiciona novo custo"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        cost_type = request.form["cost_type"]
        description = request.form["description"]
        amount = float(request.form["amount"])
        due_date_str = request.form.get("due_date")

        due_date = None
        if due_date_str:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()

        cost = ProcessCost(
            process_id=process_id,
            user_id=current_user.id,
            cost_type=cost_type,
            description=description,
            amount=amount,
            due_date=due_date,
            court_fee_type=request.form.get("court_fee_type"),
            attorney_fee_type=request.form.get("attorney_fee_type"),
            notes=request.form.get("notes"),
        )

        db.session.add(cost)
        db.session.commit()

        flash("Custo adicionado com sucesso!", "success")
        return redirect(url_for("process_management.costs", process_id=process_id))

    return render_template("processes/add_cost.html", process=process)


@bp.route("/costs/<int:cost_id>/pay", methods=["POST"])
@login_required
def mark_cost_paid(cost_id):
    """Marca custo como pago"""
    cost = ProcessCost.query.filter_by(id=cost_id, user_id=current_user.id).first_or_404()

    cost.payment_status = "paid"
    cost.payment_date = datetime.now().date()
    db.session.commit()

    flash("Custo marcado como pago!", "success")
    return redirect(url_for("process_management.costs", process_id=cost.process_id))


# ========================================
# ANEXOS DE PROCESSOS
# ========================================


@bp.route("/<int:process_id>/attachments")
@login_required
def attachments(process_id):
    """Lista anexos de um processo"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    attachments_query = ProcessAttachment.query.filter_by(process_id=process_id, status="active")
    attachments = attachments_query.order_by(ProcessAttachment.created_at.desc()).all()

    return render_template("processes/attachments.html", process=process, attachments=attachments)


@bp.route("/<int:process_id>/attachments/upload", methods=["GET", "POST"])
@login_required
def upload_attachment(process_id):
    """Upload de anexo"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
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

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(
                UPLOAD_FOLDER, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
            )
            file.save(file_path)

            attachment = ProcessAttachment(
                process_id=process_id,
                user_id=current_user.id,
                filename=filename,
                file_path=file_path,
                file_size=os.path.getsize(file_path),
                file_type=file.content_type,
                file_extension=filename.rsplit(".", 1)[1].lower(),
                title=request.form["title"],
                description=request.form.get("description"),
                document_type=request.form.get("document_type"),
                tags=request.form.get("tags"),
                is_confidential="is_confidential" in request.form,
                is_visible_to_client="is_visible_to_client" in request.form,
            )

            db.session.add(attachment)
            db.session.commit()

            flash("Anexo enviado com sucesso!", "success")
            return redirect(url_for("process_management.attachments", process_id=process_id))

    return render_template("processes/upload_attachment.html", process=process)


@bp.route("/attachments/<int:attachment_id>/download")
@login_required
def download_attachment(attachment_id):
    """Download de anexo"""
    attachment = ProcessAttachment.query.filter_by(
        id=attachment_id, user_id=current_user.id
    ).first_or_404()

    attachment.mark_accessed()

    directory = os.path.dirname(attachment.file_path)
    filename = os.path.basename(attachment.file_path)

    return send_from_directory(
        directory, filename, as_attachment=True, download_name=attachment.filename
    )


# ========================================
# API ENDPOINTS
# ========================================


@bp.route("/api/<int:process_id>/movements", methods=["GET"])
@login_required
def api_movements(process_id):
    """API para listar andamentos"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    movements = (
        ProcessMovement.query.filter_by(process_id=process_id)
        .order_by(ProcessMovement.movement_date.desc())
        .all()
    )

    return jsonify(
        {
            "movements": [
                {
                    "id": m.id,
                    "date": m.movement_date.isoformat(),
                    "description": m.description,
                    "type": m.movement_type,
                    "important": m.is_important,
                    "requires_action": m.requires_action,
                }
                for m in movements
            ]
        }
    )


@bp.route("/api/<int:process_id>/costs/summary", methods=["GET"])
@login_required
def api_costs_summary(process_id):
    """API para resumo de custos"""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    costs = ProcessCost.query.filter_by(process_id=process_id).all()

    total_pending = sum(cost.amount for cost in costs if cost.payment_status == "pending")
    total_paid = sum(cost.amount for cost in costs if cost.payment_status == "paid")
    total_overdue = sum(cost.amount for cost in costs if cost.is_overdue())

    return jsonify(
        {
            "total_pending": float(total_pending),
            "total_paid": float(total_paid),
            "total_overdue": float(total_overdue),
            "total_costs": len(costs),
        }
    )
