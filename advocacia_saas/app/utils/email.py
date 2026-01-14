"""
Utilitários de email
"""

from flask import current_app, render_template, url_for
from flask_mail import Mail, Message

mail = Mail()


def send_email(to, subject, template, **kwargs):
    """
    Envia email usando template
    """
    if not current_app.config.get("MAIL_SERVER"):
        # Email não configurado, skip silenciosamente
        current_app.logger.info(
            f"Email não enviado (não configurado): {subject} para {to}"
        )
        return False

    try:
        msg = Message(
            subject=subject,
            recipients=[to] if isinstance(to, str) else to,
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        current_app.logger.info(f"Email enviado: {subject} para {to}")
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email: {e}")
        return False


def send_office_invite_email(invite):
    """
    Envia email de convite para escritório usando Resend.

    Args:
        invite: Objeto OfficeInvite com os dados do convite

    Returns:
        bool: True se enviou com sucesso, False caso contrário
    """
    from datetime import datetime, timezone

    from app.models import OFFICE_ROLES, User
    from app.services.email_service import EmailService

    # Buscar dados necessários
    office = invite.office
    inviter = User.query.get(invite.invited_by_id)
    role_info = OFFICE_ROLES.get(invite.role, {})

    # Verificar se usuário já tem conta
    existing_user = User.query.filter_by(email=invite.email.lower()).first()

    # Calcular dias até expiração
    now = datetime.now(timezone.utc)
    expires_delta = invite.expires_at - now
    expires_in_days = max(0, expires_delta.days)

    # Gerar URL do convite
    invite_url = url_for(
        "office.accept_invite_page", token=invite.token, _external=True
    )

    # Enviar email via Resend (EmailService)
    return EmailService.send_office_invite(
        invite_email=invite.email,
        invite_url=invite_url,
        office_name=office.name,
        inviter_name=inviter.full_name or inviter.username
        if inviter
        else "Um administrador",
        role_name=role_info.get("name", invite.role.title()),
        role_description=role_info.get("description", ""),
        expires_in_days=expires_in_days,
        expires_at=invite.expires_at.strftime("%d/%m/%Y às %H:%M"),
        has_account=existing_user is not None,
    )
