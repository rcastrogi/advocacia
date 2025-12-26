"""
Utilitários de email
"""

from flask import current_app, render_template
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
        return

    try:
        msg = Message(
            subject=subject,
            recipients=[to] if isinstance(to, str) else to,
            sender=current_app.config.get(
                "MAIL_DEFAULT_SENDER", "noreply@advocaciasaas.com"
            ),
        )
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        current_app.logger.info(f"Email enviado: {subject} para {to}")
    except Exception as e:
        current_app.logger.error(f"Erro ao enviar email: {e}")
        # Não relançar erro para não quebrar o fluxo da aplicação
