"""
Rotas do Programa de Indicação

Sistema de indicação com proteção anti-fraude:
- Créditos só são concedidos após primeiro pagamento
- Limite mensal de indicações com recompensa
- Validação de CPF e email únicos
"""

from datetime import datetime, timezone
from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    request,
    jsonify,
    current_app,
    session
)
from flask_login import login_required, current_user

from app import db
from app.referral import bp
from app.models import Referral, ReferralCode, User, UserCredits


@bp.route("/")
@login_required
def dashboard():
    """Painel do programa de indicação."""
    # Obtém ou cria código do usuário
    referral_code = ReferralCode.get_or_create(current_user)
    
    # Estatísticas
    stats = Referral.get_user_stats(current_user.id)
    
    # Lista de indicações
    referrals = Referral.query.filter_by(
        referrer_id=current_user.id
    ).order_by(Referral.created_at.desc()).limit(20).all()
    
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
            "max_monthly": Referral.MAX_REFERRALS_PER_MONTH
        }
    )


@bp.route("/r/<code>")
def landing(code):
    """
    Landing page do link de indicação.
    Armazena o código na sessão e redireciona para registro.
    """
    # Valida o código
    referral_code = ReferralCode.query.filter_by(code=code.upper(), is_active=True).first()
    
    if not referral_code:
        flash("Código de indicação inválido ou expirado.", "warning")
        return redirect(url_for("main.index"))
    
    # Se usuário já está logado, não pode usar indicação
    if current_user.is_authenticated:
        flash("Você já possui uma conta. Indicações são apenas para novos usuários.", "info")
        return redirect(url_for("main.dashboard"))
    
    # Incrementa cliques
    referral_code.increment_clicks()
    
    # Armazena na sessão
    session["referral_code"] = code.upper()
    session["referrer_id"] = referral_code.user_id
    
    # Redireciona para página de registro com destaque do bônus
    return render_template(
        "referral/landing.html",
        referrer=referral_code.user,
        bonus_credits=Referral.REFERRED_BONUS_CREDITS,
        referral_code=code.upper()
    )


@bp.route("/api/stats")
@login_required
def api_stats():
    """API para obter estatísticas de indicação."""
    stats = Referral.get_user_stats(current_user.id)
    referral_code = ReferralCode.get_or_create(current_user)
    
    return jsonify({
        "success": True,
        "code": referral_code.code,
        "stats": stats,
        "clicks": referral_code.total_clicks
    })


@bp.route("/api/share", methods=["POST"])
@login_required
def api_share():
    """Registra compartilhamento do link."""
    referral_code = ReferralCode.get_or_create(current_user)
    
    # Log do compartilhamento (opcional)
    platform = request.json.get("platform", "unknown")
    current_app.logger.info(
        f"Referral share: user={current_user.id}, code={referral_code.code}, platform={platform}"
    )
    
    return jsonify({"success": True})


@bp.route("/api/validate/<code>")
def api_validate_code(code):
    """Valida se um código de indicação existe e está ativo."""
    referral_code = ReferralCode.query.filter_by(code=code.upper(), is_active=True).first()
    
    if referral_code:
        return jsonify({
            "valid": True,
            "referrer_name": referral_code.user.full_name or referral_code.user.username
        })
    
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
    existing = Referral.query.filter_by(referred_email=email.lower()).first()
    if existing:
        # Atualiza com o user_id
        existing.referred_id = user_id
        existing.status = "registered"
        existing.registered_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Atualiza contadores
        code_obj = ReferralCode.query.filter_by(code=referral_code).first()
        if code_obj:
            code_obj.increment_registrations()
        
        return existing
    
    # Cria nova referência
    referral = Referral(
        referrer_id=referrer_id,
        referred_id=user_id,
        referred_email=email.lower(),
        referral_code=referral_code,
        status="registered",
        registered_at=datetime.now(timezone.utc),
        referred_ip=request.remote_addr,
        referred_user_agent=request.user_agent.string[:500] if request.user_agent else None
    )
    db.session.add(referral)
    db.session.commit()
    
    # Atualiza contadores
    code_obj = ReferralCode.query.filter_by(code=referral_code).first()
    if code_obj:
        code_obj.increment_registrations()
    
    return referral


def process_referral_conversion(user_id, payment_id, payment_amount):
    """
    Chamado quando um usuário faz o primeiro pagamento.
    Concede as recompensas ao indicador e indicado.
    """
    referral = Referral.process_conversion(user_id, payment_id, payment_amount)
    
    if referral and referral.reward_granted:
        # Atualiza contadores
        code_obj = ReferralCode.query.filter_by(code=referral.referral_code).first()
        if code_obj:
            code_obj.increment_conversions()
        
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
            "max_monthly": Referral.MAX_REFERRALS_PER_MONTH
        }
    )
