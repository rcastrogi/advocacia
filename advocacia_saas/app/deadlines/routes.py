"""
Rotas de gerenciamento de prazos
"""

from datetime import datetime, timedelta

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.deadlines import bp
from app.models import Client, Deadline

# Email temporariamente desabilitado
try:
    from app.utils.email import send_email
except ImportError:

    def send_email(*args, **kwargs):
        """Placeholder quando utils.email não existe"""
        pass


@bp.route("/")
@login_required
def index():
    """Lista todos os prazos"""
    # Filtros
    status = request.args.get("status", "pending")
    deadline_type = request.args.get("type")

    query = Deadline.query.filter_by(user_id=current_user.id)

    if status and status != "all":
        query = query.filter_by(status=status)

    if deadline_type:
        query = query.filter_by(deadline_type=deadline_type)

    # Ordenar por data
    deadlines = query.order_by(Deadline.deadline_date.asc()).all()

    # Separar por urgência
    urgent = [d for d in deadlines if d.is_urgent()]
    upcoming = [d for d in deadlines if not d.is_urgent() and d.status == "pending"]

    return render_template(
        "deadlines/index.html",
        urgent_deadlines=urgent,
        upcoming_deadlines=upcoming,
        all_deadlines=deadlines,
    )


@bp.route("/calendar")
@login_required
def calendar():
    """Calendário visual de prazos"""
    # Buscar todos os prazos do mês atual
    today = datetime.utcnow()
    start_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Próximos 3 meses
    end_month = start_month + timedelta(days=90)

    deadlines = (
        Deadline.query.filter(
            Deadline.user_id == current_user.id,
            Deadline.deadline_date >= start_month,
            Deadline.deadline_date <= end_month,
            Deadline.status == "pending",
        )
        .order_by(Deadline.deadline_date)
        .all()
    )

    # Formatar para FullCalendar
    events = []
    for deadline in deadlines:
        color = "#dc3545" if deadline.is_urgent() else "#007bff"
        events.append(
            {
                "id": deadline.id,
                "title": deadline.title,
                "start": deadline.deadline_date.isoformat(),
                "description": deadline.description,
                "type": deadline.deadline_type,
                "color": color,
                "url": url_for("deadlines.view", deadline_id=deadline.id),
            }
        )

    return render_template("deadlines/calendar.html", events=events)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """Criar novo prazo"""
    if request.method == "POST":
        try:
            title = request.form.get("title")
            description = request.form.get("description")
            deadline_type = request.form.get("deadline_type")
            deadline_date = datetime.strptime(
                request.form.get("deadline_date"), "%Y-%m-%dT%H:%M"
            )
            alert_days_before = int(request.form.get("alert_days_before", 7))
            count_business_days = request.form.get("count_business_days") == "on"
            client_id = request.form.get("client_id")

            # Criar deadline
            deadline = Deadline(
                user_id=current_user.id,
                title=title,
                description=description,
                deadline_type=deadline_type,
                deadline_date=deadline_date,
                alert_days_before=alert_days_before,
                count_business_days=count_business_days,
                client_id=int(client_id) if client_id else None,
            )

            db.session.add(deadline)
            db.session.commit()

            flash("Prazo criado com sucesso!", "success")
            return redirect(url_for("deadlines.view", deadline_id=deadline.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar prazo: {str(e)}", "error")

    # GET
    clients = (
        Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    )
    return render_template("deadlines/new.html", clients=clients)


@bp.route("/<int:deadline_id>")
@login_required
def view(deadline_id):
    """Ver detalhes do prazo"""
    deadline = Deadline.query.get_or_404(deadline_id)

    if deadline.user_id != current_user.id:
        flash("Acesso negado", "error")
        return redirect(url_for("deadlines.index"))

    return render_template("deadlines/view.html", deadline=deadline)


@bp.route("/<int:deadline_id>/edit", methods=["GET", "POST"])
@login_required
def edit(deadline_id):
    """Editar prazo"""
    deadline = Deadline.query.get_or_404(deadline_id)

    if deadline.user_id != current_user.id:
        flash("Acesso negado", "error")
        return redirect(url_for("deadlines.index"))

    if request.method == "POST":
        try:
            deadline.title = request.form.get("title")
            deadline.description = request.form.get("description")
            deadline.deadline_type = request.form.get("deadline_type")
            deadline.deadline_date = datetime.strptime(
                request.form.get("deadline_date"), "%Y-%m-%dT%H:%M"
            )
            deadline.alert_days_before = int(request.form.get("alert_days_before", 7))
            deadline.count_business_days = (
                request.form.get("count_business_days") == "on"
            )

            db.session.commit()
            flash("Prazo atualizado com sucesso!", "success")
            return redirect(url_for("deadlines.view", deadline_id=deadline.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar prazo: {str(e)}", "error")

    clients = (
        Client.query.filter_by(user_id=current_user.id).order_by(Client.name).all()
    )
    return render_template("deadlines/edit.html", deadline=deadline, clients=clients)


@bp.route("/<int:deadline_id>/complete", methods=["POST"])
@login_required
def complete(deadline_id):
    """Marcar prazo como cumprido"""
    deadline = Deadline.query.get_or_404(deadline_id)

    if deadline.user_id != current_user.id:
        return jsonify({"error": "Acesso negado"}), 403

    notes = request.json.get("notes")
    deadline.mark_completed(notes=notes)

    return jsonify({"success": True, "message": "Prazo marcado como cumprido"})


@bp.route("/<int:deadline_id>/delete", methods=["POST"])
@login_required
def delete(deadline_id):
    """Excluir prazo"""
    deadline = Deadline.query.get_or_404(deadline_id)

    if deadline.user_id != current_user.id:
        return jsonify({"error": "Acesso negado"}), 403

    db.session.delete(deadline)
    db.session.commit()

    return jsonify({"success": True, "message": "Prazo excluído com sucesso"})


@bp.route("/api/upcoming")
@login_required
def api_upcoming():
    """API: Próximos prazos (para dashboard)"""
    days = request.args.get("days", 7, type=int)

    deadline_date = datetime.utcnow() + timedelta(days=days)

    deadlines = (
        Deadline.query.filter(
            Deadline.user_id == current_user.id,
            Deadline.status == "pending",
            Deadline.deadline_date <= deadline_date,
        )
        .order_by(Deadline.deadline_date)
        .limit(10)
        .all()
    )

    return jsonify({"deadlines": [d.to_dict() for d in deadlines]})


@bp.route("/api/send-alerts", methods=["POST"])
def api_send_alerts():
    """API: Enviar alertas de prazos próximos (cron job)"""
    # TODO: Adicionar autenticação de API key
    from flask import current_app

    # Buscar prazos que precisam de alerta
    deadlines = Deadline.query.filter(
        Deadline.status == "pending", Deadline.alert_sent.is_(False)
    ).all()

    alerts_sent = 0

    for deadline in deadlines:
        days_until = deadline.days_until()

        # Enviar alerta se estiver dentro do prazo configurado
        if 0 <= days_until <= deadline.alert_days_before:
            try:
                # Enviar email
                send_email(
                    to=deadline.user.email,
                    subject=f"⚠️ Prazo próximo: {deadline.title}",
                    template="emails/deadline_alert.html",
                    deadline=deadline,
                    days_until=days_until,
                )

                # Criar notificação
                from app.models import Notification

                Notification.create_notification(
                    user_id=deadline.user_id,
                    notification_type="deadline",
                    title="Prazo próximo",
                    message=f"{deadline.title} vence em {days_until} dias",
                    link=url_for("deadlines.view", deadline_id=deadline.id),
                )

                # Marcar como enviado
                deadline.alert_sent = True
                deadline.alert_sent_at = datetime.utcnow()
                alerts_sent += 1

            except Exception as e:
                current_app.logger.error(f"Erro ao enviar alerta: {str(e)}")

    db.session.commit()

    return jsonify({"success": True, "alerts_sent": alerts_sent})
