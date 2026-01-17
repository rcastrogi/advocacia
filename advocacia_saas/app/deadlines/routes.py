"""
Rotas de gerenciamento de prazos
"""

import os
from datetime import datetime, timedelta

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.deadlines import bp
from app.models import Client, Deadline
from app.utils.email import send_email
from app.utils.pagination import PaginationHelper


@bp.route("/")
@login_required
def index():
    """Lista todos os prazos com paginação"""
    # Filtros
    status = request.args.get("status", "pending")
    deadline_type = request.args.get("type")

    query = Deadline.query.filter_by(user_id=current_user.id)

    if status and status != "all":
        query = query.filter_by(status=status)

    if deadline_type:
        query = query.filter_by(deadline_type=deadline_type)

    # Ordenar por data
    query = query.order_by(Deadline.deadline_date.asc())

    # Paginação
    pagination = PaginationHelper(
        query=query, per_page=20, filters={"status": status, "type": deadline_type}
    )

    deadlines = pagination.items

    # Separar por urgência
    urgent = [d for d in deadlines if d.is_urgent()]
    upcoming = [d for d in deadlines if not d.is_urgent() and d.status == "pending"]

    return render_template(
        "deadlines/index.html",
        urgent_deadlines=urgent,
        upcoming_deadlines=upcoming,
        all_deadlines=deadlines,
        pagination=pagination.to_dict(),
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
    """API: Enviar alertas de prazos próximos (cron job)

    Requer header: X-API-Key com valor de CRON_API_KEY
    """
    from flask import current_app

    # Autenticação por API key
    api_key = request.headers.get("X-API-Key")
    expected_key = os.environ.get("CRON_API_KEY")

    if not expected_key:
        current_app.logger.warning(
            "CRON_API_KEY não configurada - endpoint desabilitado"
        )
        return jsonify({"error": "Endpoint não configurado"}), 503

    if not api_key or api_key != expected_key:
        current_app.logger.warning(
            f"Tentativa de acesso não autorizado ao cron de alertas"
        )
        return jsonify({"error": "API key inválida"}), 401

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


# ==================== BLOQUEIOS DE AGENDA ====================


@bp.route("/blocks")
@login_required
def blocks_list():
    """Lista todos os bloqueios de agenda do usuário"""
    from app.models import AgendaBlock

    blocks = (
        AgendaBlock.query.filter_by(user_id=current_user.id)
        .order_by(AgendaBlock.created_at.desc())
        .all()
    )

    return render_template("deadlines/blocks_list.html", blocks=blocks)


@bp.route("/blocks/new", methods=["GET", "POST"])
@login_required
def block_new():
    """Criar novo bloqueio de agenda"""
    import json

    from app.models import AgendaBlock

    if request.method == "POST":
        try:
            title = request.form.get("title")
            description = request.form.get("description")
            block_type = request.form.get("block_type", "recurring")

            # Dias da semana (para recorrente)
            weekdays = request.form.getlist("weekdays")
            weekdays_json = json.dumps([int(d) for d in weekdays]) if weekdays else None

            # Período do dia ou horário específico
            time_type = request.form.get("time_type", "period")

            if time_type == "all_day":
                all_day = True
                day_period = None
                start_time = None
                end_time = None
            elif time_type == "period":
                all_day = False
                day_period = request.form.get("day_period")
                start_time = None
                end_time = None
            else:  # specific
                all_day = False
                day_period = None
                start_time_str = request.form.get("start_time")
                end_time_str = request.form.get("end_time")
                start_time = (
                    datetime.strptime(start_time_str, "%H:%M").time()
                    if start_time_str
                    else None
                )
                end_time = (
                    datetime.strptime(end_time_str, "%H:%M").time()
                    if end_time_str
                    else None
                )

            # Datas (para bloqueio único ou período)
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date_str
                else None
            )
            end_date = (
                datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date_str
                else None
            )

            # Cor
            color = request.form.get("color", "#6c757d")

            block = AgendaBlock(
                user_id=current_user.id,
                title=title,
                description=description,
                block_type=block_type,
                weekdays=weekdays_json,
                start_time=start_time,
                end_time=end_time,
                all_day=all_day,
                day_period=day_period,
                start_date=start_date,
                end_date=end_date,
                color=color,
                is_active=True,
            )

            db.session.add(block)
            db.session.commit()

            flash("Bloqueio de agenda criado com sucesso!", "success")
            return redirect(url_for("deadlines.blocks_list"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar bloqueio: {str(e)}", "danger")

    return render_template("deadlines/block_form.html", block=None)


@bp.route("/blocks/<int:block_id>/edit", methods=["GET", "POST"])
@login_required
def block_edit(block_id):
    """Editar bloqueio de agenda"""
    import json

    from app.models import AgendaBlock

    block = AgendaBlock.query.get_or_404(block_id)

    if block.user_id != current_user.id:
        flash("Acesso negado", "danger")
        return redirect(url_for("deadlines.blocks_list"))

    if request.method == "POST":
        try:
            block.title = request.form.get("title")
            block.description = request.form.get("description")
            block.block_type = request.form.get("block_type", "recurring")

            # Dias da semana
            weekdays = request.form.getlist("weekdays")
            block.weekdays = (
                json.dumps([int(d) for d in weekdays]) if weekdays else None
            )

            # Período do dia ou horário específico
            time_type = request.form.get("time_type", "period")

            if time_type == "all_day":
                block.all_day = True
                block.day_period = None
                block.start_time = None
                block.end_time = None
            elif time_type == "period":
                block.all_day = False
                block.day_period = request.form.get("day_period")
                block.start_time = None
                block.end_time = None
            else:
                block.all_day = False
                block.day_period = None
                start_time_str = request.form.get("start_time")
                end_time_str = request.form.get("end_time")
                block.start_time = (
                    datetime.strptime(start_time_str, "%H:%M").time()
                    if start_time_str
                    else None
                )
                block.end_time = (
                    datetime.strptime(end_time_str, "%H:%M").time()
                    if end_time_str
                    else None
                )

            # Datas
            start_date_str = request.form.get("start_date")
            end_date_str = request.form.get("end_date")
            block.start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date_str
                else None
            )
            block.end_date = (
                datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date_str
                else None
            )

            block.color = request.form.get("color", "#6c757d")

            db.session.commit()

            flash("Bloqueio atualizado com sucesso!", "success")
            return redirect(url_for("deadlines.blocks_list"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar bloqueio: {str(e)}", "danger")

    return render_template("deadlines/block_form.html", block=block)


@bp.route("/blocks/<int:block_id>/delete", methods=["POST"])
@login_required
def block_delete(block_id):
    """Excluir bloqueio de agenda"""
    from app.models import AgendaBlock

    block = AgendaBlock.query.get_or_404(block_id)

    if block.user_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    db.session.delete(block)
    db.session.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"success": True, "message": "Bloqueio excluído com sucesso"})

    flash("Bloqueio excluído com sucesso!", "success")
    return redirect(url_for("deadlines.blocks_list"))


@bp.route("/blocks/<int:block_id>/toggle", methods=["POST"])
@login_required
def block_toggle(block_id):
    """Ativar/desativar bloqueio de agenda"""
    from app.models import AgendaBlock

    block = AgendaBlock.query.get_or_404(block_id)

    if block.user_id != current_user.id:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    block.is_active = not block.is_active
    db.session.commit()

    status = "ativado" if block.is_active else "desativado"
    return jsonify(
        {"success": True, "message": f"Bloqueio {status}", "is_active": block.is_active}
    )


@bp.route("/api/blocks")
@login_required
def api_blocks():
    """API: Retorna bloqueios para o calendário"""
    from app.models import AgendaBlock

    # Período para gerar eventos
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    try:
        start_date = (
            datetime.strptime(start_str[:10], "%Y-%m-%d").date()
            if start_str
            else datetime.utcnow().date()
        )
        end_date = (
            datetime.strptime(end_str[:10], "%Y-%m-%d").date()
            if end_str
            else (datetime.utcnow() + timedelta(days=90)).date()
        )
    except:
        start_date = datetime.utcnow().date()
        end_date = (datetime.utcnow() + timedelta(days=90)).date()

    blocks = AgendaBlock.query.filter_by(user_id=current_user.id, is_active=True).all()

    events = []
    for block in blocks:
        events.extend(block.to_calendar_events(start_date, end_date))

    return jsonify(events)
