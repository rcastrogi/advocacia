"""
Sistema de Notificações Inteligentes
Gerencia o envio de notificações respeitando as preferências do usuário.
"""

from datetime import datetime, timezone

from app import db
from app.models import (
    Notification,
    NotificationPreferences,
    NotificationQueue,
    User,
)


# Mapeamento de tipos de notificação para categorias
NOTIFICATION_TYPE_MAP = {
    # Prazos
    "deadline_overdue": "deadline",
    "deadline_today": "deadline",
    "deadline_urgent": "deadline",
    "deadline_warning": "deadline",
    # Movimentações
    "process_movement": "movement",
    "process_update": "movement",
    # Pagamentos
    "payment_due": "payment",
    "payment_received": "payment",
    "credit_low": "payment",
    # Petições/IA
    "petition_ready": "petition",
    "ai_limit": "petition",
    # Sistema
    "system": "system",
    "password_expiring": "system",
}

# Prioridades por tipo
NOTIFICATION_PRIORITY = {
    "deadline_overdue": 4,  # Urgente
    "deadline_today": 4,  # Urgente
    "deadline_urgent": 3,  # Alta
    "deadline_warning": 2,  # Média
    "process_movement": 2,  # Média
    "process_update": 1,  # Baixa
    "payment_due": 3,  # Alta
    "payment_received": 1,  # Baixa
    "credit_low": 2,  # Média
    "petition_ready": 2,  # Média
    "ai_limit": 2,  # Média
    "system": 1,  # Baixa
    "password_expiring": 3,  # Alta
}


def get_notification_category(notification_type):
    """Retorna a categoria de um tipo de notificação."""
    return NOTIFICATION_TYPE_MAP.get(notification_type, "system")


def get_notification_priority(notification_type):
    """Retorna a prioridade de um tipo de notificação."""
    return NOTIFICATION_PRIORITY.get(notification_type, 2)


def send_smart_notification(
    user_id,
    notification_type,
    title,
    message,
    link=None,
    data=None,
    force_channels=None,
):
    """
    Envia notificação inteligente respeitando as preferências do usuário.

    Args:
        user_id: ID do usuário
        notification_type: Tipo da notificação (ex: 'deadline_overdue')
        title: Título da notificação
        message: Mensagem da notificação
        link: URL para ação relacionada (opcional)
        data: Dados extras em dict (opcional)
        force_channels: Lista de canais para forçar envio (ignora preferências)

    Returns:
        dict: Resultado do envio por canal
    """
    prefs = NotificationPreferences.get_or_create(user_id)
    category = get_notification_category(notification_type)
    priority = get_notification_priority(notification_type)

    results = {
        "in_app": False,
        "email": False,
        "push": False,
        "queued_for_digest": False,
    }

    # === In-App (sempre verifica) ===
    if force_channels and "in_app" in force_channels:
        should_in_app = True
    else:
        should_in_app = prefs.should_notify(category, "in_app", priority)

    if should_in_app:
        try:
            Notification.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
            )
            results["in_app"] = True
        except Exception as e:
            print(f"Erro ao criar notificação in-app: {e}")

    # === Email ===
    if force_channels and "email" in force_channels:
        should_email = True
    else:
        should_email = prefs.should_notify(category, "email", priority)

    if should_email:
        # Verificar se deve ir para digest
        if (
            prefs.digest_enabled
            and priority < 3
            and not (force_channels and "email" in force_channels)
        ):
            # Adicionar à fila do digest
            NotificationQueue.add_to_queue(
                user_id=user_id,
                notification_type=notification_type,
                channel="email",
                title=title,
                message=message,
                priority=priority,
                link=link,
                data=data,
            )
            # Marcar como digest
            queue_item = NotificationQueue.query.filter_by(
                user_id=user_id,
                notification_type=notification_type,
                channel="email",
                status="pending",
            ).order_by(NotificationQueue.created_at.desc()).first()
            if queue_item:
                queue_item.status = "digest"
                db.session.commit()
            results["queued_for_digest"] = True
        else:
            # Enviar email imediatamente
            results["email"] = _send_email_notification(
                user_id, notification_type, title, message, link
            )

    # === Push ===
    if force_channels and "push" in force_channels:
        should_push = True
    else:
        should_push = prefs.should_notify(category, "push", priority)

    if should_push:
        results["push"] = _send_push_notification(
            user_id, notification_type, title, message, link
        )

    return results


def _send_email_notification(user_id, notification_type, title, message, link=None):
    """Envia notificação por email."""
    try:
        from app.processes.email_notifications import send_email_notification

        user = db.session.get(User, user_id)
        if not user or not user.email:
            return False

        # Template HTML básico
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #2563eb; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Petitio</h1>
            </div>
            <div style="padding: 30px; background: #f8f9fa;">
                <h2 style="color: #333;">{title}</h2>
                <p style="color: #666; font-size: 16px;">{message}</p>
                {f'<a href="{link}" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 20px;">Ver Detalhes</a>' if link else ''}
            </div>
            <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>Você recebeu este email porque tem notificações ativas no Petitio.</p>
                <p><a href="#">Gerenciar preferências de notificação</a></p>
            </div>
        </div>
        """

        return send_email_notification(user, title, html_content)
    except Exception as e:
        print(f"Erro ao enviar email de notificação: {e}")
        return False


def _send_push_notification(user_id, notification_type, title, message, link=None):
    """Envia notificação push via service worker."""
    try:
        from app.api.routes import send_push_to_user

        return send_push_to_user(user_id, title, message, link)
    except Exception as e:
        print(f"Erro ao enviar push notification: {e}")
        return False


def send_digest(user_id):
    """
    Envia digest consolidado de notificações para um usuário.

    Args:
        user_id: ID do usuário

    Returns:
        bool: True se enviado com sucesso
    """
    try:
        from app.processes.email_notifications import send_email_notification

        prefs = NotificationPreferences.get_or_create(user_id)
        if not prefs.digest_enabled:
            return False

        # Buscar notificações pendentes para digest
        pending = NotificationQueue.get_pending_digest(user_id)
        if not pending:
            return False

        user = db.session.get(User, user_id)
        if not user or not user.email:
            return False

        # Agrupar por categoria
        grouped = {}
        for item in pending:
            category = get_notification_category(item.notification_type)
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)

        # Construir HTML do digest
        category_names = {
            "deadline": "Prazos",
            "movement": "Movimentações",
            "payment": "Pagamentos",
            "petition": "Petições/IA",
            "system": "Sistema",
        }

        items_html = ""
        for category, items in grouped.items():
            items_html += f"""
            <div style="margin-bottom: 20px;">
                <h3 style="color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px;">
                    {category_names.get(category, category)} ({len(items)})
                </h3>
                <ul style="list-style: none; padding: 0;">
            """
            for item in items[:5]:  # Limitar a 5 por categoria
                items_html += f"""
                <li style="padding: 10px; background: #fff; margin-bottom: 5px; border-radius: 4px;">
                    <strong>{item.title}</strong><br>
                    <span style="color: #666; font-size: 14px;">{item.message[:100]}{'...' if len(item.message) > 100 else ''}</span>
                </li>
                """
            if len(items) > 5:
                items_html += f'<li style="color: #999;">+ {len(items) - 5} notificações adicionais</li>'
            items_html += "</ul></div>"

        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #2563eb; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">📬 Resumo de Notificações</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Petitio - {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>
            <div style="padding: 30px; background: #f8f9fa;">
                <p style="color: #666;">Olá {user.full_name or user.username},</p>
                <p style="color: #666;">Aqui está o resumo das suas notificações:</p>
                {items_html}
                <div style="text-align: center; margin-top: 30px;">
                    <a href="#" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">
                        Ver Todas as Notificações
                    </a>
                </div>
            </div>
            <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>Você recebeu este resumo porque ativou o digest no Petitio.</p>
                <p><a href="#">Gerenciar preferências de notificação</a></p>
            </div>
        </div>
        """

        # Enviar email
        title = f"📬 Resumo de Notificações - {datetime.now().strftime('%d/%m/%Y')}"
        success = send_email_notification(user, title, html_content)

        if success:
            # Marcar como enviadas
            for item in pending:
                item.status = "sent"
                item.sent_at = datetime.now(timezone.utc)
            prefs.last_digest_sent = datetime.now(timezone.utc)
            db.session.commit()

        return success

    except Exception as e:
        print(f"Erro ao enviar digest: {e}")
        return False


def process_pending_digests():
    """
    Processa todos os digests pendentes (para ser chamado via cron/scheduler).
    Deve ser executado a cada hora para verificar horários de envio.
    """
    now = datetime.now(timezone.utc)
    current_hour = now.hour

    # Buscar usuários com digest ativo e horário correspondente
    prefs_list = NotificationPreferences.query.filter_by(digest_enabled=True).all()

    for prefs in prefs_list:
        # Verificar horário de envio
        if prefs.digest_time:
            send_hour = prefs.digest_time.hour
            if current_hour != send_hour:
                continue

        # Verificar frequência
        if prefs.digest_frequency == "weekly":
            # Semanal: enviar apenas às segundas-feiras
            if now.weekday() != 0:
                continue

        # Verificar se já enviou hoje
        if prefs.last_digest_sent:
            if prefs.last_digest_sent.date() == now.date():
                continue

        # Enviar digest
        send_digest(prefs.user_id)


def create_deadline_notification(process, notification_type):
    """
    Cria notificação inteligente para prazos processuais.

    Args:
        process: Objeto Process
        notification_type: 'deadline_overdue', 'deadline_today', 'deadline_urgent', 'deadline_warning'
    """
    titles = {
        "deadline_overdue": f"⚠️ PRAZO VENCIDO - {process.title or process.process_number}",
        "deadline_today": f"📅 Prazo HOJE - {process.title or process.process_number}",
        "deadline_urgent": f"⏰ Prazo Urgente - {process.title or process.process_number}",
        "deadline_warning": f"📋 Prazo Próximo - {process.title or process.process_number}",
    }

    messages = {
        "deadline_overdue": f"O prazo do processo {process.process_number or process.title} está vencido! Ação imediata necessária.",
        "deadline_today": f"O prazo do processo {process.process_number or process.title} vence hoje ({process.next_deadline.strftime('%d/%m/%Y')}).",
        "deadline_urgent": f"O prazo do processo {process.process_number or process.title} está próximo de vencer.",
        "deadline_warning": f"Lembrete: O processo {process.process_number or process.title} tem prazo em breve ({process.next_deadline.strftime('%d/%m/%Y')}).",
    }

    link = f"/processes/{process.id}"

    return send_smart_notification(
        user_id=process.user_id,
        notification_type=notification_type,
        title=titles.get(notification_type, "Notificação de Prazo"),
        message=messages.get(notification_type, "Você tem uma notificação de prazo."),
        link=link,
        data={"process_id": process.id, "deadline": str(process.next_deadline)},
    )
