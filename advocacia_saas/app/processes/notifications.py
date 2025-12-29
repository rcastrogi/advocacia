from datetime import datetime, timedelta, timezone

from flask import current_app

from app import db
from app.models import Process, ProcessNotification, SavedPetition


def create_process_notification(
    user_id, process_id, notification_type, title, message, metadata=None
):
    """Cria uma nova notificação de processo."""

    notification = ProcessNotification(
        user_id=user_id,
        process_id=process_id,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata=metadata or {},
    )

    db.session.add(notification)
    db.session.commit()

    return notification


def check_deadline_notifications():
    """Verifica prazos próximos e cria notificações."""

    # Prazos vencendo hoje
    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    week_from_now = today + timedelta(days=7)

    # Buscar processos com prazos próximos
    urgent_processes = Process.query.filter(
        Process.next_deadline.isnot(None), Process.next_deadline <= week_from_now
    ).all()

    notifications_created = 0

    for process in urgent_processes:
        days_until = process.days_until_deadline()

        # Determinar tipo de notificação baseado no prazo
        if days_until < 0:
            # Prazo vencido
            if not _notification_exists(process.id, "deadline_overdue", today):
                create_process_notification(
                    user_id=process.user_id,
                    process_id=process.id,
                    notification_type="deadline_overdue",
                    title=f"Prazo vencido: {process.title}",
                    message=f"O prazo processual venceu em {abs(days_until)} dia(s). Processo: {process.process_number or 'Sem número'}",
                    metadata={
                        "days_overdue": abs(days_until),
                        "deadline_date": process.next_deadline.isoformat(),
                    },
                )
                notifications_created += 1

        elif days_until == 0:
            # Vence hoje
            if not _notification_exists(process.id, "deadline_today", today):
                create_process_notification(
                    user_id=process.user_id,
                    process_id=process.id,
                    notification_type="deadline_today",
                    title=f"Prazo vence hoje: {process.title}",
                    message=f"O prazo processual vence hoje. Processo: {process.process_number or 'Sem número'}",
                    metadata={"deadline_date": process.next_deadline.isoformat()},
                )
                notifications_created += 1

        elif days_until <= 3:
            # Vence em até 3 dias
            if not _notification_exists(process.id, "deadline_urgent", today):
                create_process_notification(
                    user_id=process.user_id,
                    process_id=process.id,
                    notification_type="deadline_urgent",
                    title=f"Prazo urgente: {process.title}",
                    message=f"O prazo processual vence em {days_until} dia(s). Processo: {process.process_number or 'Sem número'}",
                    metadata={
                        "days_until": days_until,
                        "deadline_date": process.next_deadline.isoformat(),
                    },
                )
                notifications_created += 1

        elif days_until <= 7:
            # Vence em até 7 dias
            if not _notification_exists(process.id, "deadline_warning", today):
                create_process_notification(
                    user_id=process.user_id,
                    process_id=process.id,
                    notification_type="deadline_warning",
                    title=f"Prazo próximo: {process.title}",
                    message=f"O prazo processual vence em {days_until} dia(s). Processo: {process.process_number or 'Sem número'}",
                    metadata={
                        "days_until": days_until,
                        "deadline_date": process.next_deadline.isoformat(),
                    },
                )
                notifications_created += 1

    return notifications_created


def check_petitions_without_number():
    """Verifica petições sem número de processo e cria notificações."""

    # Buscar petições finalizadas sem número
    petitions = SavedPetition.query.filter(
        SavedPetition.process_number.is_(None) | (SavedPetition.process_number == ""),
        SavedPetition.status == "completed",
    ).all()

    notifications_created = 0
    today = datetime.now(timezone.utc).date()

    # Agrupar por usuário
    user_petitions = {}
    for petition in petitions:
        if petition.user_id not in user_petitions:
            user_petitions[petition.user_id] = []
        user_petitions[petition.user_id].append(petition)

    for user_id, user_petitions_list in user_petitions.items():
        count = len(user_petitions_list)

        # Criar notificação se não existir hoje
        if not _user_notification_exists(user_id, "petitions_without_number", today):
            create_process_notification(
                user_id=user_id,
                process_id=None,
                notification_type="petitions_without_number",
                title=f"{count} petição(ões) sem número de processo",
                message=f"Você tem {count} petição(ões) finalizada(s) que ainda não possuem número de processo. Adicione os números para manter a organização.",
                metadata={
                    "petition_count": count,
                    "petition_ids": [p.id for p in user_petitions_list],
                },
            )
            notifications_created += 1

    return notifications_created


def check_status_changes():
    """Verifica mudanças de status recentes e cria notificações."""

    # Buscar processos atualizados recentemente (últimas 24h)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    recent_processes = Process.query.filter(Process.updated_at >= yesterday).all()

    notifications_created = 0

    for process in recent_processes:
        # Verificar se houve mudança significativa de status
        # Por enquanto, apenas notificar sobre processos atualizados
        # Em uma implementação completa, compararíamos com o status anterior

        if not _notification_exists(
            process.id, "status_updated", datetime.now(timezone.utc).date()
        ):
            create_process_notification(
                user_id=process.user_id,
                process_id=process.id,
                notification_type="status_updated",
                title=f"Processo atualizado: {process.title}",
                message=f"O processo {process.process_number or 'Sem número'} foi atualizado. Status atual: {process.get_status_text()}",
                metadata={
                    "new_status": process.status,
                    "updated_at": process.updated_at.isoformat(),
                },
            )
            notifications_created += 1

    return notifications_created


def _notification_exists(process_id, notification_type, date):
    """Verifica se já existe uma notificação do tipo para o processo na data especificada."""

    return (
        ProcessNotification.query.filter(
            ProcessNotification.process_id == process_id,
            ProcessNotification.notification_type == notification_type,
            db.func.date(ProcessNotification.created_at) == date,
        ).first()
        is not None
    )


def _user_notification_exists(user_id, notification_type, date):
    """Verifica se já existe uma notificação do tipo para o usuário na data especificada."""

    return (
        ProcessNotification.query.filter(
            ProcessNotification.user_id == user_id,
            ProcessNotification.notification_type == notification_type,
            db.func.date(ProcessNotification.created_at) == date,
        ).first()
        is not None
    )


def get_unread_notifications(user_id, limit=50):
    """Retorna notificações não lidas do usuário."""

    return (
        ProcessNotification.query.filter_by(user_id=user_id, read=False)
        .order_by(ProcessNotification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(notification_id, user_id):
    """Marca uma notificação como lida."""

    notification = ProcessNotification.query.filter_by(
        id=notification_id, user_id=user_id
    ).first()

    if notification:
        notification.mark_as_read()
        db.session.commit()
        return True

    return False


def run_notification_checks():
    """Executa todas as verificações de notificação."""

    total_notifications = 0

    try:
        total_notifications += check_deadline_notifications()
        total_notifications += check_petitions_without_number()
        total_notifications += check_status_changes()

        current_app.logger.info(
            f"Verificações de notificação concluídas. {total_notifications} notificações criadas."
        )

    except Exception as e:
        current_app.logger.error(f"Erro durante verificações de notificação: {str(e)}")

    return total_notifications
