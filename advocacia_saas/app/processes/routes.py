from datetime import date, timedelta, timezone, datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.decorators import lawyer_required
from app.models import Client, Process, SavedPetition
from app.processes import bp
from app.processes.forms import ProcessForm
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
    ongoing_processes = Process.query.filter_by(user_id=current_user.id, status="ongoing").count()

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
        .filter((SavedPetition.process_number.is_(None)) | (SavedPetition.process_number == ""))
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
        .filter((SavedPetition.process_number.is_(None)) | (SavedPetition.process_number == ""))
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


# =============================================================================
# CRUD de Processos
# =============================================================================


def _get_client_choices():
    """Retorna lista de clientes para o select."""
    clients = Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    choices = [("", "Nenhum cliente vinculado")]
    choices.extend([(str(c.id), c.name) for c in clients])
    return choices


@bp.route("/new", methods=["GET", "POST"])
@login_required
@lawyer_required
def create():
    """Criar novo processo."""
    form = ProcessForm()
    form.client_id.choices = _get_client_choices()

    if form.validate_on_submit():
        # Verificar se número do processo já existe (se fornecido)
        if form.process_number.data:
            existing = Process.query.filter_by(
                process_number=form.process_number.data
            ).first()
            if existing:
                flash("Este número de processo já está cadastrado.", "danger")
                return render_template(
                    "processes/form.html",
                    title="Novo Processo",
                    form=form,
                    is_edit=False,
                )

        process = Process(
            user_id=current_user.id,
            process_number=form.process_number.data or None,
            title=form.title.data,
            plaintiff=form.plaintiff.data or None,
            defendant=form.defendant.data or None,
            client_id=form.client_id.data or None,
            court=form.court.data or None,
            court_instance=form.court_instance.data or None,
            jurisdiction=form.jurisdiction.data or None,
            district=form.district.data or None,
            judge=form.judge.data or None,
            status=form.status.data,
            distribution_date=form.distribution_date.data,
            next_deadline=form.next_deadline.data,
            deadline_description=form.deadline_description.data or None,
            priority=form.priority.data,
        )

        db.session.add(process)
        db.session.commit()

        flash(f"Processo '{process.title}' criado com sucesso!", "success")
        return redirect(url_for("processes.view", process_id=process.id))

    return render_template(
        "processes/form.html",
        title="Novo Processo",
        form=form,
        is_edit=False,
    )


@bp.route("/<int:process_id>")
@login_required
@lawyer_required
def view(process_id):
    """Visualizar detalhes do processo."""
    process = Process.query.filter_by(
        id=process_id, user_id=current_user.id
    ).first_or_404()

    # Buscar petições vinculadas
    petitions = process.petitions

    # Buscar movimentações (se existir)
    movements = []
    if hasattr(process, "movements"):
        movements = process.movements.order_by("created_at desc").limit(10).all()

    return render_template(
        "processes/view.html",
        title=f"Processo: {process.title}",
        process=process,
        petitions=petitions,
        movements=movements,
    )


@bp.route("/<int:process_id>/edit", methods=["GET", "POST"])
@login_required
@lawyer_required
def edit(process_id):
    """Editar processo existente."""
    process = Process.query.filter_by(
        id=process_id, user_id=current_user.id
    ).first_or_404()

    form = ProcessForm(obj=process)
    form.client_id.choices = _get_client_choices()

    if form.validate_on_submit():
        # Verificar se número do processo já existe (se mudou)
        if form.process_number.data and form.process_number.data != process.process_number:
            existing = Process.query.filter_by(
                process_number=form.process_number.data
            ).first()
            if existing:
                flash("Este número de processo já está cadastrado.", "danger")
                return render_template(
                    "processes/form.html",
                    title=f"Editar: {process.title}",
                    form=form,
                    process=process,
                    is_edit=True,
                )

        # Atualizar campos
        process.process_number = form.process_number.data or None
        process.title = form.title.data
        process.plaintiff = form.plaintiff.data or None
        process.defendant = form.defendant.data or None
        process.client_id = form.client_id.data or None
        process.court = form.court.data or None
        process.court_instance = form.court_instance.data or None
        process.jurisdiction = form.jurisdiction.data or None
        process.district = form.district.data or None
        process.judge = form.judge.data or None
        process.status = form.status.data
        process.distribution_date = form.distribution_date.data
        process.next_deadline = form.next_deadline.data
        process.deadline_description = form.deadline_description.data or None
        process.priority = form.priority.data
        process.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        flash("Processo atualizado com sucesso!", "success")
        return redirect(url_for("processes.view", process_id=process.id))

    # Preencher client_id como string para o select
    if process.client_id:
        form.client_id.data = str(process.client_id)

    return render_template(
        "processes/form.html",
        title=f"Editar: {process.title}",
        form=form,
        process=process,
        is_edit=True,
    )


@bp.route("/<int:process_id>/delete", methods=["POST"])
@login_required
@lawyer_required
def delete(process_id):
    """Excluir processo."""
    process = Process.query.filter_by(
        id=process_id, user_id=current_user.id
    ).first_or_404()

    title = process.title
    db.session.delete(process)
    db.session.commit()

    flash(f"Processo '{title}' excluído com sucesso.", "success")
    return redirect(url_for("processes.list_processes"))
