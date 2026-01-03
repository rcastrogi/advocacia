#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Newsletter semanal de roadmap
Envia toda segunda 8h mostrando:
- O que saiu na semana
- Top votadas
- Estatísticas
"""

import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app import create_app, db
from app.models import RoadmapItem, User
from app.models_roadmap_votes import RoadmapVote

app = create_app()


def get_week_start():
    """Retorna segunda-feira passada às 00:00"""
    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()  # 0 = segunda, 6 = domingo
    monday = now - timedelta(
        days=days_since_monday,
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )
    return monday


def get_this_month():
    """Retorna YYYY-MM do mês atual"""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def send_email(to_email, subject, html_content):
    """Envia email via SMTP"""
    try:
        # Configurar SMTP (usar suas credenciais)
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("FROM_EMAIL", smtp_user)

        if not smtp_user or not smtp_password:
            print(f"[!] SMTP não configurado - email não enviado para {to_email}")
            return False

        # Criar mensagem
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email

        # Adicionar corpo em HTML
        msg.attach(MIMEText(html_content, "html"))

        # Conectar e enviar
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"[!] Erro ao enviar email: {str(e)}")
        return False


def generate_newsletter_html(user_email):
    """Gera conteúdo HTML da newsletter"""
    week_start = get_week_start()
    week_end = week_start + timedelta(days=7)
    current_month = get_this_month()

    # O que saiu essa semana
    new_items = RoadmapItem.query.filter(
        RoadmapItem.status == "completed",
        RoadmapItem.implemented_at >= week_start,
        RoadmapItem.implemented_at <= week_end,
    ).all()

    # Top votadas este mês
    top_voted_query = (
        db.session.query(
            RoadmapItem.id,
            RoadmapItem.title,
            RoadmapItem.status,
            db.func.sum(RoadmapVote.votes_spent).label("total_votes"),
        )
        .join(RoadmapVote, RoadmapItem.id == RoadmapVote.roadmap_item_id)
        .filter(RoadmapVote.billing_period == current_month)
        .group_by(RoadmapItem.id, RoadmapItem.title, RoadmapItem.status)
        .order_by(db.func.sum(RoadmapVote.votes_spent).desc())
        .limit(5)
        .all()
    )

    # Estatísticas
    total_items = RoadmapItem.query.count()
    completed_items = RoadmapItem.query.filter_by(status="completed").count()
    in_progress_items = RoadmapItem.query.filter_by(status="in_progress").count()
    planned_items = RoadmapItem.query.filter_by(status="planned").count()

    completion_percentage = (
        int((completed_items / total_items * 100)) if total_items > 0 else 0
    )

    # Montar HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #333; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }}
            h2 {{ color: #2563eb; margin-top: 30px; }}
            .item {{ background: #f9f9f9; padding: 12px; margin: 10px 0; border-left: 4px solid #2563eb; border-radius: 4px; }}
            .status {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
            .status-completed {{ background: #d1fae5; color: #065f46; }}
            .status-in_progress {{ background: #fef3c7; color: #78350f; }}
            .status-planned {{ background: #e0e7ff; color: #3730a3; }}
            .stat-box {{ display: inline-block; width: 45%; padding: 15px; margin: 10px 2%; background: #f0f9ff; border-radius: 8px; text-align: center; }}
            .stat-number {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
            .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
            .progress-bar {{ width: 100%; height: 20px; background: #e5e7eb; border-radius: 10px; overflow: hidden; }}
            .progress-fill {{ height: 100%; background: #22c55e; width: {completion_percentage}%; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #999; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Roadmap Semanal - {week_start.strftime("%d/%m/%Y")}</h1>
            
            <h2>✅ O que saiu essa semana</h2>
    """

    if new_items:
        for item in new_items:
            html += f"""
            <div class="item">
                <strong>{item.title}</strong>
                <span class="status status-completed">Concluído</span>
                <br>
                <small>Implementado em {item.implemented_at.strftime("%d/%m/%Y")}</small>
            </div>
            """
    else:
        html += "<p style='color: #999;'>Nenhuma feature concluída essa semana</p>"

    # Top votadas
    html += "<h2>🔥 Mais votadas (votos desta semana)</h2>"

    if top_voted_query:
        for rank, (item_id, title, status, total_votes) in enumerate(
            top_voted_query, 1
        ):
            status_class = f"status-{status}"
            html += f"""
            <div class="item">
                <strong>{rank}. {title}</strong>
                <span class="status {status_class}">{status.replace("_", " ").title()}</span>
                <br>
                <strong style="color: #2563eb;">{int(total_votes)} votos</strong>
            </div>
            """
    else:
        html += "<p style='color: #999;'>Nenhum voto registrado ainda</p>"

    # Estatísticas
    html += f"""
    <h2>📊 Estatísticas do Roadmap</h2>
    <div class="progress-bar">
        <div class="progress-fill"></div>
    </div>
    <p style="text-align: center; margin-top: 10px;"><strong>{completion_percentage}% concluído</strong></p>
    
    <div>
        <div class="stat-box">
            <div class="stat-number">{completed_items}</div>
            <div class="stat-label">Concluídos</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{in_progress_items}</div>
            <div class="stat-label">Em progresso</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{planned_items}</div>
            <div class="stat-label">Planejados</div>
        </div>
        <div class="stat-box">
            <div class="stat-number">{total_items}</div>
            <div class="stat-label">Total</div>
        </div>
    </div>
    
    <div class="footer">
        <p>Newsletter automática gerada em {datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M")} UTC</p>
        <p>Para votar nas próximas features, <a href="https://seu-site.com/roadmap">clique aqui</a></p>
    </div>
    </div>
    </body>
    </html>
    """

    return html


def send_newsletter():
    """Envia newsletter para todos os usuários ativos"""
    print("\n" + "=" * 80)
    print("NEWSLETTER SEMANAL DE ROADMAP")
    print("=" * 80 + "\n")

    with app.app_context():
        # Buscar usuários ativos
        users = User.query.filter(User.is_active == True, User.email.isnot(None)).all()

        print(f"Preparando newsletter para {len(users)} usuários...\n")

        sent = 0
        failed = 0

        for user in users:
            try:
                html_content = generate_newsletter_html(user.email)
                subject = f"📋 Seu Roadmap Semanal - {datetime.now(timezone.utc).strftime('%d/%m/%Y')}"

                if send_email(user.email, subject, html_content):
                    sent += 1
                    print(f"[✓] Email enviado para {user.email}")
                else:
                    failed += 1
                    print(f"[!] Falha ao enviar para {user.email}")
            except Exception as e:
                failed += 1
                print(f"[!] Erro processando {user.email}: {str(e)}")

        print(f"\n[✓] Newsletter concluída!")
        print(f"    → {sent} emails enviados com sucesso")
        print(f"    → {failed} falhas")


if __name__ == "__main__":
    send_newsletter()
