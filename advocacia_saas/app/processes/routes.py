"""
Processes Routes - Rotas HTTP para processos judiciais.

Controllers delegando para os serviços especializados.
"""

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import lawyer_required
from app.processes import bp
from app.processes.forms import ProcessForm
from app.processes.services import ProcessService


@bp.route("/")
@login_required
@lawyer_required
def dashboard():
    """Dashboard principal de processos."""
    data = ProcessService.get_dashboard_data(current_user.id)

    return render_template(
        "processes/dashboard.html",
        title="Processos - Dashboard",
        **data,
    )


@bp.route("/list")
@login_required
@lawyer_required
def list_processes():
    """Lista todos os processos."""
    data = ProcessService.list_processes(
        user_id=current_user.id,
        status=request.args.get("status"),
        search=request.args.get("search"),
        per_page=20,
    )

    return render_template(
        "processes/list.html",
        title="Lista de Processos",
        **data,
    )


@bp.route("/pending-petitions")
@login_required
@lawyer_required
def pending_petitions():
    """Lista petições sem número de processo."""
    page = request.args.get("page", 1, type=int)
    petitions = ProcessService.get_pending_petitions(current_user.id, page)

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


@bp.route("/new", methods=["GET", "POST"])
@login_required
@lawyer_required
def create():
    """Criar novo processo."""
    form = ProcessForm()
    form.client_id.choices = ProcessService.get_client_choices(current_user.id)

    if form.validate_on_submit():
        result = ProcessService.create_process(
            user_id=current_user.id,
            title=form.title.data,
            process_number=form.process_number.data,
            plaintiff=form.plaintiff.data,
            defendant=form.defendant.data,
            client_id=form.client_id.data,
            court=form.court.data,
            court_instance=form.court_instance.data,
            jurisdiction=form.jurisdiction.data,
            district=form.district.data,
            judge=form.judge.data,
            status=form.status.data,
            distribution_date=form.distribution_date.data,
            next_deadline=form.next_deadline.data,
            deadline_description=form.deadline_description.data,
            priority=form.priority.data,
        )

        if not result.success:
            flash(result.error_message, "danger")
            return render_template(
                "processes/form.html",
                title="Novo Processo",
                form=form,
                is_edit=False,
            )

        flash(f"Processo '{result.process.title}' criado com sucesso!", "success")
        return redirect(url_for("processes.view", process_id=result.process.id))

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
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

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
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

    form = ProcessForm(obj=process)
    form.client_id.choices = ProcessService.get_client_choices(current_user.id)

    if form.validate_on_submit():
        result = ProcessService.update_process(
            process=process,
            title=form.title.data,
            process_number=form.process_number.data,
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

        if not result.success:
            flash(result.error_message, "danger")
            return render_template(
                "processes/form.html",
                title=f"Editar: {process.title}",
                form=form,
                process=process,
                is_edit=True,
            )

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
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

    title = ProcessService.delete_process(process)
    flash(f"Processo '{title}' excluído com sucesso.", "success")
    return redirect(url_for("processes.list_processes"))
