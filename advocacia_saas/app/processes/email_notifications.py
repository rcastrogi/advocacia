"""
Sistema de notificações por email para processos
"""

import os
from datetime import datetime, timedelta

from flask import render_template
from flask_mail import Mail, Message

from app import db
from app.models import Process, ProcessNotification, User

mail = Mail()


def init_mail(app):
    """Inicializa o sistema de email"""
    global mail
    mail.init_app(app)


def send_email_notification(user, subject, html_content, text_content=None):
    """Envia notificação por email"""
    try:
        msg = Message(subject=subject, recipients=[user.email], html=html_content)

        if text_content:
            msg.body = text_content

        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False


def send_deadline_notification(process, notification_type, days_until=None):
    """Envia notificação de prazo"""
    user = process.user

    if notification_type == "deadline_overdue":
        subject = f"PRAZO VENCIDO - Processo {process.process_number or process.title}"
        template = "emails/deadline_overdue.html"
        context = {
            "process": process,
            "user": user,
            "deadline": process.next_deadline,
            "days_overdue": abs((process.next_deadline - datetime.now().date()).days),
        }
    elif notification_type == "deadline_today":
        subject = (
            f"PRAZO VENCE HOJE - Processo {process.process_number or process.title}"
        )
        template = "emails/deadline_today.html"
        context = {"process": process, "user": user, "deadline": process.next_deadline}
    elif notification_type == "deadline_urgent":
        subject = f"PRAZO URGENTE - Processo {process.process_number or process.title}"
        template = "emails/deadline_urgent.html"
        context = {
            "process": process,
            "user": user,
            "deadline": process.next_deadline,
            "days_until": days_until,
        }
    elif notification_type == "deadline_warning":
        subject = f"AVISO DE PRAZO - Processo {process.process_number or process.title}"
        template = "emails/deadline_warning.html"
        context = {
            "process": process,
            "user": user,
            "deadline": process.next_deadline,
            "days_until": days_until,
        }
    else:
        return False

    # Renderizar template HTML
    html_content = render_template(template, **context)

    # Enviar email
    success = send_email_notification(user, subject, html_content)

    if success:
        # Registrar envio
        notification = ProcessNotification(
            user_id=user.id,
            process_id=process.id,
            notification_type=notification_type,
            title=subject,
            message=f"Notificação enviada por email sobre prazo do processo {process.title}",
            sent_at=datetime.now(),
            extra_data={"email_sent": True, "template": template},
        )
        db.session.add(notification)
        db.session.commit()

    return success


def send_movement_notification(process, movement):
    """Envia notificação de novo andamento"""
    user = process.user

    subject = f"Novo Andamento - Processo {process.process_number or process.title}"

    # Renderizar template
    html_content = render_template(
        "emails/new_movement.html", process=process, movement=movement, user=user
    )

    success = send_email_notification(user, subject, html_content)

    if success:
        # Registrar envio
        notification = ProcessNotification(
            user_id=user.id,
            process_id=process.id,
            notification_type="new_movement",
            title=subject,
            message=f"Novo andamento registrado: {movement.description[:100]}...",
            sent_at=datetime.now(),
            extra_data={"email_sent": True, "movement_id": movement.id},
        )
        db.session.add(notification)
        db.session.commit()

    return success


def send_cost_notification(process, cost):
    """Envia notificação de custo vencido ou próximo do vencimento"""
    user = process.user

    if cost.is_overdue():
        subject = f"CUSTO VENCIDO - Processo {process.process_number or process.title}"
        template = "emails/cost_overdue.html"
    else:
        subject = f"CUSTO PRÓXIMO DO VENCIMENTO - Processo {process.process_number or process.title}"
        template = "emails/cost_due_soon.html"

    # Renderizar template
    html_content = render_template(template, process=process, cost=cost, user=user)

    success = send_email_notification(user, subject, html_content)

    if success:
        notification_type = "cost_overdue" if cost.is_overdue() else "cost_due_soon"
        notification = ProcessNotification(
            user_id=user.id,
            process_id=process.id,
            notification_type=notification_type,
            title=subject,
            message=f"Notificação sobre custo: {cost.description}",
            sent_at=datetime.now(),
            extra_data={"email_sent": True, "cost_id": cost.id},
        )
        db.session.add(notification)
        db.session.commit()

    return success


def check_and_send_notifications():
    """Verifica e envia notificações pendentes"""
    today = datetime.now().date()

    # Notificações de prazo
    processes_with_deadlines = Process.query.filter(
        Process.next_deadline.isnot(None)
    ).all()

    notifications_sent = 0

    for process in processes_with_deadlines:
        days_until = (process.next_deadline - today).days

        # Prazo vencido
        if days_until < 0 and not _notification_exists(
            process.id, "deadline_overdue", today
        ):
            if send_deadline_notification(process, "deadline_overdue"):
                notifications_sent += 1

        # Prazo vence hoje
        elif days_until == 0 and not _notification_exists(
            process.id, "deadline_today", today
        ):
            if send_deadline_notification(process, "deadline_today"):
                notifications_sent += 1

        # Prazo urgente (3 dias)
        elif (
            days_until <= 3
            and days_until > 0
            and not _notification_exists(process.id, "deadline_urgent", today)
        ):
            if send_deadline_notification(process, "deadline_urgent", days_until):
                notifications_sent += 1

        # Aviso de prazo (7 dias)
        elif (
            days_until <= 7
            and days_until > 3
            and not _notification_exists(process.id, "deadline_warning", today)
        ):
            if send_deadline_notification(process, "deadline_warning", days_until):
                notifications_sent += 1

    # Verificar custos próximos do vencimento
    from app.models import ProcessCost

    due_costs = ProcessCost.query.filter(
        ProcessCost.payment_status == "pending",
        ProcessCost.due_date.isnot(None),
        ProcessCost.due_date <= today + timedelta(days=7),
    ).all()

    for cost in due_costs:
        notification_type = "cost_overdue" if cost.is_overdue() else "cost_due_soon"
        if not _notification_exists(cost.process_id, notification_type, today, cost.id):
            if send_cost_notification(cost.process, cost):
                notifications_sent += 1

    return notifications_sent


def _notification_exists(process_id, notification_type, date, related_id=None):
    """Verifica se notificação já foi enviada hoje"""
    query = ProcessNotification.query.filter(
        ProcessNotification.process_id == process_id,
        ProcessNotification.notification_type == notification_type,
        ProcessNotification.sent_at >= date,
        ProcessNotification.sent_at < date + timedelta(days=1),
    )

    if related_id:
        query = query.filter(
            ProcessNotification.extra_data.contains({"cost_id": related_id})
        )

    return query.first() is not None
