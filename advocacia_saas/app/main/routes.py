from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from app.main import bp
from app.models import Client


@bp.route("/")
def index():
    return render_template("index.html", title="Petitio")


@bp.route("/dashboard")
@login_required
def dashboard():
    # Get client statistics
    total_clients = Client.query.filter_by(lawyer_id=current_user.id).count()
    recent_clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.created_at.desc())
        .limit(5)
        .all()
    )

    stats = {"total_clients": total_clients, "recent_clients": recent_clients}

    return render_template("dashboard.html", title="Dashboard", stats=stats)


@bp.route("/peticionador")
@login_required
def peticionador():
    return render_template("peticionador.html", title="Peticionador")


@bp.route("/termos")
def terms_of_service():
    """Página de Termos de Uso"""
    return render_template("terms_of_service.html", title="Termos de Uso")


@bp.route("/privacidade")
def privacy_policy():
    """Política de Privacidade em conformidade com LGPD"""
    return render_template("privacy_policy.html", title="Política de Privacidade")


@bp.route("/lgpd")
def lgpd_info():
    """Informações sobre conformidade com LGPD"""
    return render_template("lgpd_info.html", title="Conformidade LGPD")
