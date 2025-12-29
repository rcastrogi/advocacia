from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.decorators import lawyer_required
from app.models import Client, Process, SavedPetition
from app.processes import bp
from app.processes.notifications import get_unread_notifications


@bp.route("/")
@login_required
@lawyer_required
def dashboard():
    """Dashboard principal de processos."""

    # Estatísticas básicas
    total_processes = Process.query.filter_by(user_id=current_user.id).count()
    pending_processes = Process.query.filter_by(
        user_id=current_user.id, status="pending_distribution"
    ).count()
    ongoing_processes = Process.query.filter_by(
        user_id=current_user.id, status="ongoing"
    ).count()

    # Processos recentes
    recent_processes = (
        Process.query.filter_by(user_id=current_user.id)
        .order_by(Process.updated_at.desc())
        .limit(10)
        .all()
    )

    # Petições sem número de processo
    petitions_without_number = (
        SavedPetition.query.filter_by(user_id=current_user.id)
        .filter(
            (SavedPetition.process_number.is_(None))
            | (SavedPetition.process_number == "")
        )
        .filter(SavedPetition.status == "completed")
        .order_by(SavedPetition.completed_at.desc())
        .limit(10)
        .all()
    )

    # Prazos urgentes (próximos 7 dias)
    from datetime import date, timedelta

    today = date.today()
    week_from_now = today + timedelta(days=7)

    urgent_processes = Process.query.filter(
        Process.user_id == current_user.id,
        Process.next_deadline.isnot(None),
        Process.next_deadline <= week_from_now,
    ).count()

    # Notificações não lidas
    unread_notifications = get_unread_notifications(current_user.id, limit=10)

    # Processos por status
    processes_by_status = (
        db.session.query(Process.status, func.count(Process.id).label("count"))
        .filter_by(user_id=current_user.id)
        .group_by(Process.status)
        .all()
    )

    stats = {
        "total_processes": total_processes,
        "pending_processes": pending_processes,
        "ongoing_processes": ongoing_processes,
        "petitions_without_number": len(petitions_without_number),
    }

    return render_template(
        "processes/dashboard.html",
        title="Processos - Dashboard",
        stats=stats,
        recent_processes=recent_processes,
        petitions_without_number=petitions_without_number,
        urgent_deadlines=urgent_processes,
        unread_notifications=unread_notifications,
        processes_by_status=dict(processes_by_status),
    )


@bp.route("/list")
@login_required
@lawyer_required
def list_processes():
    """Lista todos os processos."""

    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Filtros
    status_filter = request.args.get("status")
    search = request.args.get("search")

    query = Process.query.filter_by(user_id=current_user.id)

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(
            (Process.title.contains(search))
            | (Process.process_number.contains(search))
            | (Process.plaintiff.contains(search))
            | (Process.defendant.contains(search))
        )

    processes = query.order_by(Process.updated_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "processes/list.html",
        title="Lista de Processos",
        processes=processes,
        status_filter=status_filter,
        search=search,
    )


@bp.route("/pending-petitions")
@login_required
@lawyer_required
def pending_petitions():
    """Lista petições sem número de processo."""

    page = request.args.get("page", 1, type=int)
    per_page = 20

    petitions = (
        SavedPetition.query.filter_by(user_id=current_user.id)
        .filter(
            (SavedPetition.process_number.is_(None))
            | (SavedPetition.process_number == "")
        )
        .filter(SavedPetition.status == "completed")
        .order_by(SavedPetition.completed_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "processes/pending_petitions.html",
        title="Petições Pendentes de Número",
        petitions=petitions,
    )


@bp.route("/reports")
@login_required
@lawyer_required
def reports():
    """Página de relatórios de processos."""

    return render_template("processes/reports.html", title="Relatórios de Processos")
