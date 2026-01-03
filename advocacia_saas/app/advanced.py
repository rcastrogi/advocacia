"""
Rotas para funcionalidades avançadas do sistema de processos.
Inclui calendário, automação e relatórios.
"""

import json
from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, func, or_

from app import db
from app.decorators import master_required
from app.models import (
    CalendarEvent,
    Notification,
    Process,
    ProcessAttachment,
    ProcessAutomation,
    ProcessCost,
    ProcessMovement,
    ProcessReport,
)

# Blueprint para funcionalidades avançadas
advanced_bp = Blueprint("advanced", __name__, url_prefix="/advanced")


# =============================================================================
# ROTAS DO CALENDÁRIO
# =============================================================================


@advanced_bp.route("/calendar")
@login_required
def calendar():
    """Página principal do calendário."""
    # Contar solicitações pendentes
    client_ids = [client.id for client in current_user.clients.all()]
    pending_requests_count = 0

    if client_ids:
        pending_requests_count = CalendarEvent.query.filter(
            CalendarEvent.client_id.in_(client_ids), CalendarEvent.status == "requested"
        ).count()

    return render_template("advanced/calendar.html", pending_requests_count=pending_requests_count)


@advanced_bp.route("/api/calendar/events")
@login_required
def get_calendar_events():
    """API para obter eventos do calendário."""
    start = request.args.get("start")
    end = request.args.get("end")

    # Eventos criados pelo advogado
    query1 = CalendarEvent.query.filter_by(user_id=current_user.id)

    # Eventos relacionados aos clientes do advogado (incluindo solicitações)
    client_ids = [client.id for client in current_user.clients.all()]
    query2 = (
        CalendarEvent.query.filter(CalendarEvent.client_id.in_(client_ids)) if client_ids else None
    )

    # Combinar queries
    if query2:
        from sqlalchemy import union_all

        combined_query = query1.union_all(query2)
    else:
        combined_query = query1

    if start:
        start_date = datetime.fromisoformat(start.replace("Z", "+00:00"))
        combined_query = combined_query.filter(CalendarEvent.start_datetime >= start_date)

    if end:
        end_date = datetime.fromisoformat(end.replace("Z", "+00:00"))
        combined_query = combined_query.filter(CalendarEvent.start_datetime <= end_date)

    events = combined_query.all()

    # Formatar para FullCalendar
    calendar_events = []
    for event in events:
        # Determinar se é evento próprio ou de cliente
        is_own_event = event.user_id == current_user.id
        is_request = event.status == "requested"

        title = event.title
        if is_request and not is_own_event:
            title = f"📋 {title}"  # Adicionar ícone para solicitações

        calendar_events.append(
            {
                "id": event.id,
                "title": title,
                "start": event.start_datetime.isoformat(),
                "end": event.end_datetime.isoformat(),
                "allDay": event.all_day,
                "backgroundColor": get_event_color(event),
                "borderColor": get_event_color(event),
                "textColor": "#ffffff",
                "extendedProps": {
                    "type": event.event_type,
                    "priority": event.priority,
                    "status": event.status,
                    "location": event.location,
                    "description": event.description,
                    "process_id": event.process_id,
                    "client_id": event.client_id,
                    "client_name": event.client.full_name if event.client else None,
                    "is_own_event": is_own_event,
                    "is_request": is_request,
                },
            }
        )

    return jsonify(calendar_events)


def get_event_color(event):
    """Retorna cor baseada no tipo e prioridade do evento."""
    # Solicitações pendentes têm cor especial
    if event.status == "requested":
        return "#fd7e14"  # Laranja para solicitações pendentes

    colors = {
        "audiencia": "#dc3545",  # Vermelho
        "prazo": "#ffc107",  # Amarelo
        "reuniao": "#007bff",  # Azul
        "compromisso": "#28a745",  # Verde
    }

    base_color = colors.get(event.event_type, "#6c757d")  # Cinza padrão

    # Ajustar cor baseada na prioridade
    if event.priority == "urgent":
        # Tom mais escuro para urgente
        return adjust_color_brightness(base_color, -0.3)
    elif event.priority == "high":
        return adjust_color_brightness(base_color, -0.15)

    return base_color


def adjust_color_brightness(hex_color, factor):
    """Ajusta o brilho de uma cor hexadecimal."""
    # Simplificação: retornar cor mais escura para prioridades altas
    if factor < 0:
        return (
            "#8b0000"
            if hex_color == "#dc3545"
            else (
                "#b8860b"
                if hex_color == "#ffc107"
                else "#00008b" if hex_color == "#007bff" else "#006400"
            )
        )
    return hex_color


@advanced_bp.route("/calendar/event/new", methods=["GET", "POST"])
@login_required
def new_calendar_event():
    """Criar novo evento no calendário."""
    if request.method == "POST":
        try:
            # Dados do formulário
            title = request.form.get("title")
            description = request.form.get("description")
            start_datetime = datetime.fromisoformat(request.form.get("start_datetime"))
            end_datetime = datetime.fromisoformat(request.form.get("end_datetime"))
            all_day = request.form.get("all_day") == "on"
            event_type = request.form.get("event_type")
            priority = request.form.get("priority", "normal")
            location = request.form.get("location")
            virtual_link = request.form.get("virtual_link")
            process_id = request.form.get("process_id")
            client_id = request.form.get("client_id")
            notes = request.form.get("notes")

            # Criar evento
            event = CalendarEvent(
                user_id=current_user.id,
                title=title,
                description=description,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                all_day=all_day,
                event_type=event_type,
                priority=priority,
                location=location,
                virtual_link=virtual_link,
                process_id=int(process_id) if process_id else None,
                client_id=int(client_id) if client_id else None,
                notes=notes,
            )

            db.session.add(event)
            db.session.commit()

            flash("Evento criado com sucesso!", "success")
            return redirect(url_for("advanced.calendar"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar evento: {str(e)}", "error")
            return redirect(url_for("advanced.new_calendar_event"))

    # GET: mostrar formulário
    processes = Process.query.filter_by(user_id=current_user.id).all()
    clients = current_user.clients.all()

    return render_template("advanced/new_event.html", processes=processes, clients=clients)


@advanced_bp.route("/calendar/event/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_calendar_event(event_id):
    """Editar evento do calendário."""
    event = CalendarEvent.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            event.title = request.form.get("title")
            event.description = request.form.get("description")
            event.start_datetime = datetime.fromisoformat(request.form.get("start_datetime"))
            event.end_datetime = datetime.fromisoformat(request.form.get("end_datetime"))
            event.all_day = request.form.get("all_day") == "on"
            event.event_type = request.form.get("event_type")
            event.priority = request.form.get("priority", "normal")
            event.location = request.form.get("location")
            event.virtual_link = request.form.get("virtual_link")
            event.process_id = (
                int(request.form.get("process_id")) if request.form.get("process_id") else None
            )
            event.client_id = (
                int(request.form.get("client_id")) if request.form.get("client_id") else None
            )
            event.notes = request.form.get("notes")

            db.session.commit()

            flash("Evento atualizado com sucesso!", "success")
            return redirect(url_for("advanced.calendar"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar evento: {str(e)}", "error")

    processes = Process.query.filter_by(user_id=current_user.id).all()
    clients = current_user.clients.all()

    return render_template(
        "advanced/edit_event.html", event=event, processes=processes, clients=clients
    )


@advanced_bp.route("/calendar/event/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_calendar_event(event_id):
    """Excluir evento do calendário."""
    event = CalendarEvent.query.filter_by(id=event_id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(event)
        db.session.commit()
        flash("Evento excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir evento.", "error")

    return redirect(url_for("advanced.calendar"))


# =============================================================================
# ROTAS DE AUTOMAÇÃO
# =============================================================================


@advanced_bp.route("/automation")
@login_required
def automation():
    """Página de automação de processos."""
    automations = ProcessAutomation.query.filter_by(user_id=current_user.id).all()
    return render_template("advanced/automation.html", automations=automations)


@advanced_bp.route("/automation/new", methods=["GET", "POST"])
@login_required
def new_automation():
    """Criar nova automação."""
    if request.method == "POST":
        try:
            name = request.form.get("name")
            description = request.form.get("description")
            trigger_type = request.form.get("trigger_type")
            action_type = request.form.get("action_type")
            is_active = request.form.get("is_active") == "on"

            # Configurações específicas
            trigger_condition = {}
            action_config = {}

            # Condições do gatilho
            if trigger_type == "movement":
                trigger_condition["movement_type"] = request.form.get("movement_type")
            elif trigger_type == "deadline":
                trigger_condition["days_before"] = int(request.form.get("days_before", 7))
            elif trigger_type == "status_change":
                trigger_condition["old_status"] = request.form.get("old_status")
                trigger_condition["new_status"] = request.form.get("new_status")

            # Configuração da ação
            if action_type == "notification":
                action_config["title"] = request.form.get("notification_title")
                action_config["message"] = request.form.get("notification_message")
            elif action_type == "email":
                action_config["subject"] = request.form.get("email_subject")
                action_config["body"] = request.form.get("email_body")
                action_config["recipients"] = request.form.get("email_recipients")

            # Escopo
            applies_to_all = request.form.get("applies_to_all") == "on"
            specific_processes = request.form.get("specific_processes")
            process_types = request.form.get("process_types")

            automation = ProcessAutomation(
                user_id=current_user.id,
                name=name,
                description=description,
                trigger_type=trigger_type,
                trigger_condition=trigger_condition,
                action_type=action_type,
                action_config=action_config,
                is_active=is_active,
                applies_to_all_processes=applies_to_all,
                specific_processes=specific_processes,
                process_types=process_types,
            )

            db.session.add(automation)
            db.session.commit()

            flash("Automação criada com sucesso!", "success")
            return redirect(url_for("advanced.automation"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar automação: {str(e)}", "error")

    return render_template("advanced/new_automation.html")


@advanced_bp.route("/automation/<int:automation_id>/toggle", methods=["POST"])
@login_required
def toggle_automation(automation_id):
    """Ativar/desativar automação."""
    automation = ProcessAutomation.query.filter_by(
        id=automation_id, user_id=current_user.id
    ).first_or_404()

    automation.is_active = not automation.is_active
    db.session.commit()

    status = "ativada" if automation.is_active else "desativada"
    flash(f"Automação {status} com sucesso!", "success")

    return redirect(url_for("advanced.automation"))


@advanced_bp.route("/automation/<int:automation_id>/delete", methods=["POST"])
@login_required
def delete_automation(automation_id):
    """Excluir automação."""
    automation = ProcessAutomation.query.filter_by(
        id=automation_id, user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(automation)
        db.session.commit()
        flash("Automação excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir automação.", "error")

    return redirect(url_for("advanced.automation"))


# =============================================================================
# ROTAS DE RELATÓRIOS
# =============================================================================


@advanced_bp.route("/reports")
@login_required
def reports():
    """Página de relatórios."""
    reports_list = (
        ProcessReport.query.filter_by(user_id=current_user.id)
        .order_by(ProcessReport.created_at.desc())
        .all()
    )

    return render_template("advanced/reports.html", reports=reports_list)


@advanced_bp.route("/reports/new", methods=["GET", "POST"])
@login_required
def new_report():
    """Criar novo relatório."""
    if request.method == "POST":
        try:
            report_type = request.form.get("report_type")
            title = request.form.get("title")
            description = request.form.get("description")
            start_date = datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
            end_date = datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()

            # Filtros
            filters = {}
            if request.form.get("court_filter"):
                filters["court"] = request.form.get("court_filter")
            if request.form.get("status_filter"):
                filters["status"] = request.form.get("status_filter")

            # Criar relatório
            report = ProcessReport(
                user_id=current_user.id,
                report_type=report_type,
                title=title,
                description=description,
                start_date=start_date,
                end_date=end_date,
                filters=filters,
            )

            db.session.add(report)
            db.session.commit()

            # Gerar relatório em background
            report.generate_report()

            flash("Relatório criado e está sendo gerado!", "success")
            return redirect(url_for("advanced.reports"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao criar relatório: {str(e)}", "error")

    return render_template("advanced/new_report.html")


@advanced_bp.route("/reports/<int:report_id>")
@login_required
def view_report(report_id):
    """Visualizar relatório."""
    report = ProcessReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()

    return render_template("advanced/view_report.html", report=report)


@advanced_bp.route("/reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    """Excluir relatório."""
    report = ProcessReport.query.filter_by(id=report_id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(report)
        db.session.commit()
        flash("Relatório excluído com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir relatório.", "error")

    return redirect(url_for("advanced.reports"))


# =============================================================================
# API PARA SUGESTÕES AUTOMÁTICAS
# =============================================================================


@advanced_bp.route("/api/suggestions/next-actions/<int:process_id>")
@login_required
def get_next_actions_suggestions(process_id):
    """API para obter sugestões de próximos atos processuais."""
    process = Process.query.filter_by(id=process_id, user_id=current_user.id).first_or_404()

    suggestions = []

    # Analisar status atual e histórico para sugerir próximos atos
    last_movement = process.movements.order_by(ProcessMovement.movement_date.desc()).first()

    if process.status == "distributed":
        suggestions.append(
            {
                "action": "contestacao",
                "title": "Apresentar Contestação",
                "description": "Prazo geralmente de 15 dias para apresentar contestação",
                "priority": "high",
                "deadline_days": 15,
            }
        )

    elif process.status == "ongoing" and last_movement:
        if "sentenca" in (last_movement.description or "").lower():
            suggestions.append(
                {
                    "action": "recurso",
                    "title": "Interpor Recurso",
                    "description": "Avaliar possibilidade de recurso contra a sentença",
                    "priority": "high",
                    "deadline_days": 15,
                }
            )

    # Sugestões baseadas em custos pendentes
    pending_costs = ProcessCost.query.filter_by(
        process_id=process_id, payment_status="pending"
    ).count()

    if pending_costs > 0:
        suggestions.append(
            {
                "action": "payment",
                "title": "Regularizar Pagamentos",
                "description": f"Existem {pending_costs} custos pendentes de pagamento",
                "priority": "urgent",
                "deadline_days": 7,
            }
        )

    return jsonify(suggestions)


@advanced_bp.route("/api/processes/metrics")
@login_required
def get_processes_metrics():
    """API para métricas gerais dos processos."""
    # Contar processos por status
    status_counts = (
        db.session.query(Process.status, func.count(Process.id))
        .filter(Process.user_id == current_user.id)
        .group_by(Process.status)
        .all()
    )

    # Custos totais
    total_costs = (
        db.session.query(func.sum(ProcessCost.amount))
        .join(Process)
        .filter(Process.user_id == current_user.id)
        .scalar()
        or 0
    )

    # Processos ativos nos últimos 30 dias
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_processes = Process.query.filter(
        Process.user_id == current_user.id, Process.created_at >= thirty_days_ago
    ).count()

    # Média de tempo de resolução
    completed_processes = Process.query.filter(
        Process.user_id == current_user.id,
        Process.status == "finished",
        Process.distribution_date.isnot(None),
    ).all()

    avg_resolution_days = 0
    if completed_processes:
        total_days = sum(
            (p.updated_at.date() - p.distribution_date).days
            for p in completed_processes
            if p.distribution_date
        )
        avg_resolution_days = total_days // len(completed_processes) if total_days > 0 else 0

    metrics = {
        "status_counts": dict(status_counts),
        "total_costs": float(total_costs),
        "recent_processes": recent_processes,
        "avg_resolution_days": avg_resolution_days,
        "total_processes": sum(count for _, count in status_counts),
    }

    return jsonify(metrics)


# =============================================================================
# GESTÃO DE SOLICITAÇÕES DE REUNIÃO
# =============================================================================


@advanced_bp.route("/meeting-requests")
@login_required
def meeting_requests():
    """Página para gerenciar solicitações de reunião dos clientes."""
    # Buscar eventos com status "requested" relacionados aos clientes do advogado
    client_ids = [client.id for client in current_user.clients.all()]

    if client_ids:
        requests = (
            CalendarEvent.query.filter(
                CalendarEvent.client_id.in_(client_ids),
                CalendarEvent.status == "requested",
            )
            .order_by(CalendarEvent.created_at.desc())
            .all()
        )
    else:
        requests = []

    return render_template("advanced/meeting_requests.html", requests=requests)


@advanced_bp.route("/meeting-request/<int:event_id>/<action>", methods=["POST"])
@login_required
def handle_meeting_request(event_id, action):
    """Aprovar ou rejeitar solicitação de reunião."""

    # Verificar se o evento pertence a um cliente do advogado
    event = CalendarEvent.query.filter_by(id=event_id).first_or_404()
    client_ids = [client.id for client in current_user.clients.all()]

    if event.client_id not in client_ids:
        flash("Acesso negado. Este evento não pertence aos seus clientes.", "danger")
        return redirect(url_for("advanced.meeting_requests"))

    if action == "approve":
        # Aprovar solicitação - alterar status para "scheduled"
        event.status = "scheduled"
        event.title = event.title.replace("Solicitação: ", "")  # Remover prefixo
        event.user_id = current_user.id  # Transferir propriedade para o advogado

        # Criar notificação para o cliente
        Notification.create_notification(
            user_id=event.client.user_id,
            notification_type="meeting_approved",
            title="Reunião Agendada",
            message=f"Sua solicitação de reunião '{event.title}' foi aprovada para {event.start_datetime.strftime('%d/%m/%Y %H:%M')}.",
            link=url_for("portal.calendar"),
        )

        flash("Solicitação de reunião aprovada com sucesso!", "success")

    elif action == "reject":
        # Rejeitar solicitação
        reason = request.form.get("reason", "Sem motivo especificado")

        # Criar notificação para o cliente
        Notification.create_notification(
            user_id=event.client.user_id,
            notification_type="meeting_rejected",
            title="Reunião Não Aprovada",
            message=f"Sua solicitação de reunião '{event.title.replace('Solicitação: ', '')}' não pôde ser agendada. Motivo: {reason}",
            link=url_for("portal.calendar"),
        )

        # Remover o evento solicitado
        db.session.delete(event)

        flash("Solicitação de reunião rejeitada.", "info")

    elif action == "reschedule":
        # Reagendar - redirecionar para edição
        return redirect(url_for("advanced.edit_calendar_event", event_id=event.id))

    db.session.commit()

    return redirect(url_for("advanced.meeting_requests"))


@advanced_bp.route("/schedule-client-meeting", methods=["GET", "POST"])
@login_required
def schedule_client_meeting():
    """Agendar reunião diretamente com cliente (iniciativa do advogado)."""

    if request.method == "POST":
        try:
            title = request.form.get("title")
            description = request.form.get("description")
            start_datetime = datetime.fromisoformat(request.form.get("start_datetime"))
            end_datetime = datetime.fromisoformat(request.form.get("end_datetime"))
            client_id = request.form.get("client_id")
            process_id = request.form.get("process_id")
            location = request.form.get("location")
            virtual_link = request.form.get("virtual_link")
            notes = request.form.get("notes")

            # Verificar se o cliente pertence ao advogado
            client = current_user.clients.filter_by(id=client_id).first()
            if not client:
                flash("Cliente não encontrado ou não autorizado.", "danger")
                return redirect(request.url)

            # Criar evento diretamente (não é solicitação)
            event = CalendarEvent(
                user_id=current_user.id,
                title=title,
                description=description,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                event_type="reuniao",
                client_id=int(client_id),
                process_id=int(process_id) if process_id else None,
                location=location,
                virtual_link=virtual_link,
                notes=notes,
                status="scheduled",
                priority="normal",
            )

            db.session.add(event)
            db.session.commit()

            # Criar notificação para o cliente
            Notification.create_notification(
                user_id=client.user_id,
                notification_type="meeting_scheduled",
                title="Nova Reunião Agendada",
                message=f"Uma reunião foi agendada: '{title}' para {start_datetime.strftime('%d/%m/%Y %H:%M')}.",
                link=url_for("portal.calendar"),
            )

            flash("Reunião agendada com sucesso! O cliente foi notificado.", "success")
            return redirect(url_for("advanced.calendar"))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao agendar reunião: {str(e)}", "danger")
            return redirect(request.url)

    # GET: mostrar formulário
    clients = current_user.clients.all()
    processes = Process.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "advanced/schedule_client_meeting.html", clients=clients, processes=processes
    )
