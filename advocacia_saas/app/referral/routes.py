"""
Rotas do Programa de Indicação

Sistema de indicação com proteção anti-fraude:
- Créditos só são concedidos após primeiro pagamento
- Limite mensal de indicações com recompensa
- Validação de CPF e email únicos
"""

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Referral
from app.referral import bp
from app.referral.repository import ReferralCodeRepository, ReferralRecordRepository


@bp.route("/")
@login_required
def dashboard():
    """Painel do programa de indicação."""
    # Obtém ou cria código do usuário
    referral_code = ReferralCodeRepository.get_or_create(current_user)

    # Estatísticas
    stats = ReferralRecordRepository.get_user_stats(current_user.id)

    # Lista de indicações
    referrals = ReferralRecordRepository.get_by_referrer(current_user.id)

    # URL de compartilhamento
    share_url = url_for("referral.landing", code=referral_code.code, _external=True)

    return render_template(
        "referral/dashboard.html",
        referral_code=referral_code,
        stats=stats,
        referrals=referrals,
        share_url=share_url,
        rewards={
            "referrer": Referral.REFERRER_REWARD_CREDITS,
            "referred": Referral.REFERRED_BONUS_CREDITS,
            "max_monthly": Referral.MAX_REFERRALS_PER_MONTH,
        },
    )


@bp.route("/r/<code>")
def landing(code):
    """
    Landing page do link de indicação.
    Armazena o código na sessão e redireciona para registro.
    """
    # Valida o código
    referral_code = ReferralCodeRepository.get_by_code(code)

    if not referral_code:
        flash("Código de indicação inválido ou expirado.", "warning")
        return redirect(url_for("main.index"))

    # Se usuário já está logado, não pode usar indicação
    if current_user.is_authenticated:
        flash(
            "Você já possui uma conta. Indicações são apenas para novos usuários.",
            "info",
        )
        return redirect(url_for("main.dashboard"))

    # Incrementa cliques
    ReferralCodeRepository.increment_clicks(referral_code)

    # Armazena na sessão
    session["referral_code"] = code.upper()
    session["referrer_id"] = referral_code.user_id

    # Redireciona para página de registro com destaque do bônus
    return render_template(
        "referral/landing.html",
        referrer=referral_code.user,
        bonus_credits=Referral.REFERRED_BONUS_CREDITS,
        referral_code=code.upper(),
    )


@bp.route("/api/stats")
@login_required
def api_stats():
    """API para obter estatísticas de indicação."""
    stats = ReferralRecordRepository.get_user_stats(current_user.id)
    referral_code = ReferralCodeRepository.get_or_create(current_user)

    return jsonify(
        {
            "success": True,
            "code": referral_code.code,
            "stats": stats,
            "clicks": referral_code.total_clicks,
        }
    )


@bp.route("/api/share", methods=["POST"])
@login_required
def api_share():
    """Registra compartilhamento do link."""
    referral_code = ReferralCodeRepository.get_or_create(current_user)

    # Log do compartilhamento
    data = request.get_json() or {}
    platform = data.get("platform", "unknown")
    current_app.logger.info(
        f"Referral share: user={current_user.id}, "
        f"code={referral_code.code}, platform={platform}"
    )

    return jsonify({"success": True})


@bp.route("/api/validate/<code>")
def api_validate_code(code):
    """Valida se um código de indicação existe e está ativo."""
    referral_code = ReferralCodeRepository.get_by_code(code)

    if referral_code:
        return jsonify(
            {
                "valid": True,
                "referrer_name": referral_code.user.full_name
                or referral_code.user.username,
            }
        )

    return jsonify({"valid": False})


def process_referral_registration(email, user_id):
    """
    Chamado quando um novo usuário se registra.
    Verifica se foi indicado e atualiza o status.
    """
    referral_code = session.pop("referral_code", None)
    referrer_id = session.pop("referrer_id", None)

    if not referral_code or not referrer_id:
        return None

    # Verifica se já existe referência para este email
    existing = ReferralRecordRepository.get_by_email(email)
    if existing:
        # Atualiza com o user_id
        ReferralRecordRepository.update_referred_user(existing, user_id)

        # Atualiza contadores
        code_obj = ReferralCodeRepository.get_by_code(referral_code, active_only=False)
        if code_obj:
            ReferralCodeRepository.increment_registrations(code_obj)

        return existing

    # Cria nova referência
    referral = ReferralRecordRepository.create(
        referrer_id=referrer_id,
        referred_id=user_id,
        referred_email=email,
        referral_code=referral_code,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string if request.user_agent else None,
    )

    # Atualiza contadores
    code_obj = ReferralCodeRepository.get_by_code(referral_code, active_only=False)
    if code_obj:
        ReferralCodeRepository.increment_registrations(code_obj)

    return referral


def process_referral_conversion(user_id, payment_id, payment_amount):
    """
    Chamado quando um usuário faz o primeiro pagamento.
    Concede as recompensas ao indicador e indicado.
    """
    referral = ReferralRecordRepository.process_conversion(
        user_id, payment_id, payment_amount
    )

    if referral and referral.reward_granted:
        # Atualiza contadores
        code_obj = ReferralCodeRepository.get_by_code(
            referral.referral_code, active_only=False
        )
        if code_obj:
            ReferralCodeRepository.increment_conversions(code_obj)

        # Log
        current_app.logger.info(
            f"Referral converted: {referral.referrer_id} -> {user_id}, "
            f"credits: {referral.referrer_reward_credits} + {referral.referred_reward_credits}"
        )

    return referral


@bp.route("/how-it-works")
def how_it_works():
    """Página explicativa do programa."""
    return render_template(
        "referral/how_it_works.html",
        rewards={
            "referrer": Referral.REFERRER_REWARD_CREDITS,
            "referred": Referral.REFERRED_BONUS_CREDITS,
            "max_monthly": Referral.MAX_REFERRALS_PER_MONTH,
        },
    )
