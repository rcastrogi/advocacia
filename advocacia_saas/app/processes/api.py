from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.decorators import lawyer_required
from app.models import Process, ProcessNotification, SavedPetition, process_petitions
from app.processes import bp
from app.processes.notifications import (
    get_unread_notifications,
    mark_notification_as_read,
    run_notification_checks,
)
from app.processes.reports import get_dashboard_analytics, get_process_reports


@bp.route("/api/processes", methods=["GET"])
@login_required
@lawyer_required
def get_processes():
    """API para listar processos com filtros e paginação."""

    # Parâmetros de query
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status")
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "updated_at")
    sort_order = request.args.get("sort_order", "desc")

    # Query base
    query = Process.query.filter_by(user_id=current_user.id)

    # Aplicar filtros
    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(
            (Process.title.contains(search))
            | (Process.process_number.contains(search))
            | (Process.plaintiff.contains(search))
            | (Process.defendant.contains(search))
        )

    # Ordenação
    if sort_order == "asc":
        query = query.order_by(getattr(Process, sort_by).asc())
    else:
        query = query.order_by(getattr(Process, sort_by).desc())

    # Paginação
    processes = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify(
        {
            "processes": [
                {
                    "id": p.id,
                    "process_number": p.process_number,
                    "title": p.title,
                    "plaintiff": p.plaintiff,
                    "defendant": p.defendant,
                    "court": p.court,
                    "jurisdiction": p.jurisdiction,
                    "status": p.status,
                    "status_display": p.get_status_display()[0],
                    "status_color": p.get_status_color(),
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in processes.items
            ],
            "pagination": {
                "page": processes.page,
                "per_page": processes.per_page,
                "total": processes.total,
                "pages": processes.pages,
                "has_next": processes.has_next,
                "has_prev": processes.has_prev,
                "next_num": processes.next_num if processes.has_next else None,
                "prev_num": processes.prev_num if processes.has_prev else None,
            },
        }
    )


@bp.route("/api/processes/<int:process_id>", methods=["GET"])
@login_required
@lawyer_required
def get_process(process_id):
    """API para obter detalhes de um processo específico."""

    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    # Buscar petições relacionadas
    related_petitions = (
        SavedPetition.query.join(process_petitions)
        .filter(process_petitions.c.process_id == process_id)
        .all()
    )

    return jsonify(
        {
            "process": {
                "id": process.id,
                "process_number": process.process_number,
                "title": process.title,
                "plaintiff": process.plaintiff,
                "defendant": process.defendant,
                "court": process.court,
                "court_instance": process.court_instance,
                "jurisdiction": process.jurisdiction,
                "district": process.district,
                "judge": process.judge,
                "status": process.status,
                "status_display": process.get_status_display()[0],
                "status_color": process.get_status_color(),
                "distribution_date": (
                    process.distribution_date.isoformat() if process.distribution_date else None
                ),
                "created_at": process.created_at.isoformat(),
                "updated_at": process.updated_at.isoformat(),
            },
            "related_petitions": [
                {
                    "id": p.id,
                    "title": p.title,
                    "petition_type": p.petition_type.name if p.petition_type else None,
                    "status": p.status,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                }
                for p in related_petitions
            ],
        }
    )


@bp.route("/api/processes", methods=["POST"])
@login_required
@lawyer_required
def create_process():
    """API para criar um novo processo."""

    data = request.get_json()

    # Validação básica
    if not data.get("title"):
        return jsonify({"error": "Título é obrigatório"}), 400

    # Verificar se número do processo já existe (se fornecido)
    if data.get("process_number"):
        existing = Process.query.filter_by(
            process_number=data["process_number"], user_id=current_user.id
        ).first()
        if existing:
            return jsonify({"error": "Número do processo já existe"}), 400

    # Criar processo
    process = Process(
        user_id=current_user.id,
        process_number=data.get("process_number"),
        title=data["title"],
        plaintiff=data.get("plaintiff"),
        defendant=data.get("defendant"),
        court=data.get("court"),
        court_instance=data.get("court_instance"),
        jurisdiction=data.get("jurisdiction"),
        district=data.get("district"),
        judge=data.get("judge"),
        status=data.get("status", "pending_distribution"),
    )

    if data.get("distribution_date"):
        from datetime import datetime

        process.distribution_date = datetime.fromisoformat(data["distribution_date"])

    db.session.add(process)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Processo criado com sucesso",
                "process": {
                    "id": process.id,
                    "process_number": process.process_number,
                    "title": process.title,
                    "status": process.status,
                },
            }
        ),
        201,
    )


@bp.route("/api/processes/<int:process_id>", methods=["PUT"])
@login_required
@lawyer_required
def update_process(process_id):
    """API para atualizar um processo."""

    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    data = request.get_json()

    # Verificar se número do processo já existe (se fornecido e alterado)
    if data.get("process_number") and data["process_number"] != process.process_number:
        existing = Process.query.filter_by(
            process_number=data["process_number"], user_id=current_user.id
        ).first()
        if existing:
            return jsonify({"error": "Número do processo já existe"}), 400

    # Atualizar campos
    for field in [
        "process_number",
        "title",
        "plaintiff",
        "defendant",
        "court",
        "court_instance",
        "jurisdiction",
        "district",
        "judge",
        "status",
    ]:
        if field in data:
            setattr(process, field, data[field])

    if data.get("distribution_date"):
        from datetime import datetime

        process.distribution_date = datetime.fromisoformat(data["distribution_date"])
    elif "distribution_date" in data and data["distribution_date"] is None:
        process.distribution_date = None

    db.session.commit()

    return jsonify(
        {
            "message": "Processo atualizado com sucesso",
            "process": {
                "id": process.id,
                "process_number": process.process_number,
                "title": process.title,
                "status": process.status,
            },
        }
    )


@bp.route("/api/processes/<int:process_id>", methods=["DELETE"])
@login_required
@lawyer_required
def delete_process(process_id):
    """API para excluir um processo."""

    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    # Remover relacionamentos com petições
    db.session.execute(
        process_petitions.delete().where(process_petitions.c.process_id == process_id)
    )

    db.session.delete(process)
    db.session.commit()

    return jsonify({"message": "Processo excluído com sucesso"})


@bp.route("/api/processes/<int:process_id>/petitions/<int:petition_id>", methods=["POST"])
@login_required
@lawyer_required
def link_petition_to_process(process_id, petition_id):
    """API para vincular uma petição a um processo."""

    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()
    petition = SavedPetition.query.filter_by(id=petition_id, user_id=current_user.id).first_or_404()

    # Verificar se já está vinculado
    existing = db.session.execute(
        process_petitions.select().where(
            (process_petitions.c.process_id == process_id)
            & (process_petitions.c.petition_id == petition_id)
        )
    ).first()

    if existing:
        return jsonify({"error": "Petição já está vinculada a este processo"}), 400

    # Vincular
    db.session.execute(
        process_petitions.insert().values(
            process_id=process_id,
            petition_id=petition_id,
            relation_type=request.get_json().get("relation_type", "related"),
        )
    )

    # Se a petição não tem número, atualizar com o do processo
    if not petition.process_number and process.process_number:
        petition.process_number = process.process_number
        db.session.add(petition)

    db.session.commit()

    return jsonify({"message": "Petição vinculada com sucesso"})


@bp.route("/api/processes/<int:process_id>/petitions/<int:petition_id>", methods=["DELETE"])
@login_required
@lawyer_required
def unlink_petition_from_process(process_id, petition_id):
    """API para desvincular uma petição de um processo."""

    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()
    petition = SavedPetition.query.filter_by(id=petition_id, user_id=current_user.id).first_or_404()

    # Remover vínculo
    result = db.session.execute(
        process_petitions.delete().where(
            (process_petitions.c.process_id == process_id)
            & (process_petitions.c.petition_id == petition_id)
        )
    )

    if result.rowcount == 0:
        return jsonify({"error": "Petição não estava vinculada a este processo"}), 400

    db.session.commit()

    return jsonify({"message": "Petição desvinculada com sucesso"})


@bp.route("/api/processes/stats", methods=["GET"])
@login_required
@lawyer_required
def get_process_stats():
    """API para obter estatísticas dos processos."""

    # Contagem por status
    status_counts = (
        db.session.query(Process.status, func.count(Process.id).label("count"))
        .filter_by(user_id=current_user.id)
        .group_by(Process.status)
        .all()
    )

    # Petições sem número
    petitions_without_number = (
        SavedPetition.query.filter_by(user_id=current_user.id)
        .filter((SavedPetition.process_number.is_(None)) | (SavedPetition.process_number == ""))
        .filter(SavedPetition.status == "completed")
        .count()
    )

    # Totais
    total_processes = Process.query.filter_by(user_id=current_user.id).count()
    recent_processes = (
        Process.query.filter_by(user_id=current_user.id)
        .filter(Process.created_at >= func.date("now", "-30 days"))
        .count()
    )

    return jsonify(
        {
            "total_processes": total_processes,
            "recent_processes": recent_processes,
            "petitions_without_number": petitions_without_number,
            "status_distribution": dict(status_counts),
        }
    )


# ==========================================
# NOTIFICAÇÕES
# ==========================================


@bp.route("/api/notifications", methods=["GET"])
@login_required
@lawyer_required
def get_notifications():
    """API para obter notificações do usuário."""

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    only_unread = request.args.get("unread", "false").lower() == "true"

    query = ProcessNotification.query.filter_by(user_id=current_user.id)

    if only_unread:
        query = query.filter_by(read=False)

    notifications = query.order_by(ProcessNotification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "notifications": [
                {
                    "id": n.id,
                    "process_id": n.process_id,
                    "notification_type": n.notification_type,
                    "title": n.title,
                    "message": n.message,
                    "read": n.read,
                    "created_at": n.created_at.isoformat(),
                    "metadata": n.extra_data,
                }
                for n in notifications.items
            ],
            "pagination": {
                "page": notifications.page,
                "per_page": notifications.per_page,
                "total": notifications.total,
                "pages": notifications.pages,
                "has_next": notifications.has_next,
                "has_prev": notifications.has_prev,
            },
        }
    )


@bp.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
@lawyer_required
def mark_notification_read(notification_id):
    """API para marcar notificação como lida."""

    if mark_notification_as_read(notification_id, current_user.id):
        return jsonify({"message": "Notificação marcada como lida"})
    else:
        return jsonify({"error": "Notificação não encontrada"}), 404


@bp.route("/api/notifications/check", methods=["POST"])
@login_required
@lawyer_required
def check_notifications():
    """API para executar verificações de notificação manualmente."""

    notifications_created = run_notification_checks()

    return jsonify(
        {
            "message": f"Verificações concluídas. {notifications_created} notificações criadas.",
            "notifications_created": notifications_created,
        }
    )


# ==========================================
# RELATÓRIOS
# ==========================================


@bp.route("/api/reports/<report_type>", methods=["GET"])
@login_required
@lawyer_required
def get_report(report_type):
    """API para obter relatórios."""

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    start_date = None
    end_date = None

    if start_date_str:
        from datetime import datetime

        start_date = datetime.fromisoformat(start_date_str)
    if end_date_str:
        from datetime import datetime

        end_date = datetime.fromisoformat(end_date_str)

    report = get_process_reports(current_user.id, report_type, start_date, end_date)

    if "error" in report:
        return jsonify(report), 400

    return jsonify(report)


@bp.route("/api/analytics/dashboard", methods=["GET"])
@login_required
@lawyer_required
def get_dashboard_analytics_api():
    """API para obter analytics do dashboard."""

    analytics = get_dashboard_analytics(current_user.id)

    return jsonify(analytics)


# =============================================================================
# API DataJud - Consulta de Processos
# =============================================================================

@bp.route("/api/datajud/search", methods=["POST"])
@login_required
@lawyer_required
def search_datajud():
    """
    Consulta informações de um processo na API pública do DataJud.
    
    Body JSON:
        - process_number: Número do processo (obrigatório)
        - tribunal: Sigla do tribunal (opcional, detectado automaticamente)
    
    Returns:
        Dados do processo mapeados para o formulário ou mensagem de erro.
    """
    from app.services.datajud_service import DataJudService
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            "success": False,
            "message": "Dados não fornecidos."
        }), 400
    
    process_number = data.get("process_number", "").strip()
    tribunal = data.get("tribunal", "").strip() or None
    
    if not process_number:
        return jsonify({
            "success": False,
            "message": "Número do processo é obrigatório."
        }), 400
    
    # Consulta DataJud
    result = DataJudService.search_process(process_number, tribunal)
    
    # Sempre retorna 200 - success indica se encontrou ou não
    return jsonify(result)
