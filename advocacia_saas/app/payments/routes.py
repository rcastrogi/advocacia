"""
Rotas de pagamento - Mercado Pago Único
PIX: Pagamentos únicos instantâneos
Preapprovals: Assinaturas recorrentes automáticas
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import mercadopago
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db, limiter
from app.decorators import validate_with_schema
from app.models import BillingPlan, Payment, Subscription, User
from app.payments import bp
from app.rate_limits import ADMIN_API_LIMIT
from app.schemas import PaymentSchema, SubscriptionSchema, WebhookSchema
from app.utils.audit import AuditManager
from app.utils.error_messages import format_error_for_user

# Configurar Mercado Pago
mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = mercadopago.SDK(mp_access_token) if mp_access_token else None


def _process_referral_conversion(user_id, payment_id, payment_amount):
    """
    Processa conversão de indicação quando um pagamento é confirmado.
    Só concede créditos na primeira compra do usuário indicado.
    """
    try:
        from app.referral.routes import process_referral_conversion
        referral = process_referral_conversion(user_id, payment_id, payment_amount)
        if referral and referral.reward_granted:
            current_app.logger.info(
                f"🎁 Referral conversion: user={user_id}, referrer={referral.referrer_id}, "
                f"credits={referral.referrer_reward_credits}+{referral.referred_reward_credits}"
            )
    except Exception as e:
        # Não falhar o pagamento por erro na indicação
        current_app.logger.error(f"Erro ao processar indicação: {str(e)}")


# Planos disponíveis (carregados dinamicamente do banco)
def get_plans():
    """Carrega planos ativos do banco de dados"""
    return (
        BillingPlan.query.filter_by(active=True)
        .order_by(BillingPlan.plan_type, BillingPlan.name)
        .all()
    )


@bp.route("/plans")
@login_required
def plans():
    """Página de planos"""
    current_subscription = Subscription.query.filter_by(
        user_id=current_user.id, status="active"
    ).first()

    return render_template(
        "payments/plans.html",
        plans=get_plans(),
        current_subscription=current_subscription,
    )


@bp.route("/subscribe/<plan_slug>/<billing_period>")
@login_required
def subscribe(plan_slug, billing_period):
    """Iniciar processo de assinatura"""
    plan = BillingPlan.query.filter_by(slug=plan_slug, active=True).first()
    if not plan:
        flash("Plano inválido", "error")
        return redirect(url_for("payments.plans"))

    # Validar período de cobrança
    valid_periods = ["1m", "3m", "6m", "1y", "2y", "3y"]
    if billing_period not in valid_periods:
        flash("Período de cobrança inválido", "error")
        return redirect(url_for("payments.plans"))

    # Verificar se o plano suporta este período
    if billing_period not in plan.supported_periods:
        flash("Este plano não suporta o período selecionado", "error")
        return redirect(url_for("payments.plans"))

    # Calcular valor usando o método do modelo
    amount = plan.get_price_for_period(billing_period)
    if amount is None:
        flash("Erro ao calcular preço", "error")
        return redirect(url_for("payments.plans"))

    # Verificar se já tem assinatura ativa
    existing = Subscription.query.filter_by(
        user_id=current_user.id, status="active"
    ).first()

    if existing:
        flash("Você já possui uma assinatura ativa", "warning")
        return redirect(url_for("payments.my_subscription"))

    return render_template(
        "payments/checkout.html",
        plan_slug=plan_slug,
        plan_type=plan.plan_type,
        plan_name=plan.name,
        billing_period=billing_period,
        amount=amount,
        period_label=plan.get_period_label(billing_period),
    )


@bp.route("/create-pix-payment", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
@validate_with_schema(PaymentSchema, location="json")
def create_pix_payment():
    """Criar pagamento PIX via Mercado Pago (apenas para pay-per-use)"""
    try:
        data = request.validated_data
        amount = float(data.get("amount"))
        plan_id = data.get("plan_id")
        description = data.get("description", "Pagamento via PIX")

        if plan_id:
            plan = BillingPlan.query.get_or_404(plan_id)
            if not plan.active:
                return jsonify({"error": "Plano inválido ou inativo"}), 400
            if plan.plan_type != "per_usage":
                return jsonify(
                    {"error": "PIX disponível apenas para planos pay-per-use"}
                ), 400
            amount = max(amount, float(plan.monthly_fee))

        # Criar pagamento no Mercado Pago
        payment_data = {
            "transaction_amount": amount,
            "description": f"Petitio - {plan.name} ({billing_period})",
            "payment_method_id": "pix",
            "payer": {
                "email": current_user.email,
                "first_name": current_user.full_name or current_user.username,
            },
        }

        result = mp_sdk.payment().create(payment_data)
        payment_response = result["response"]

        if result["status"] != 201:
            return jsonify({"error": "Erro ao criar pagamento"}), 500

        # Salvar no banco
        payment = Payment(
            user_id=current_user.id,
            amount=Decimal(str(amount)),
            currency="BRL",
            payment_type="one_time",  # Pagamento único
            payment_method="pix",
            status="pending",
            gateway="mercadopago",
            gateway_payment_id=str(payment_response["id"]),
            description=payment_data["description"],
            pix_code=payment_response["point_of_interaction"]["transaction_data"][
                "qr_code"
            ],
            pix_qr_code=payment_response["point_of_interaction"]["transaction_data"][
                "qr_code_base64"
            ],
            pix_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.session.add(payment)
        db.session.commit()

        # Auditoria: pagamento criado
        AuditManager.log_payment_created(payment, current_user)

        return jsonify(
            {
                "success": True,
                "payment_id": payment.id,
                "pix_code": payment.pix_code,
                "pix_qr_code": payment.pix_qr_code,
                "expires_at": payment.pix_expires_at.isoformat(),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao criar pagamento PIX: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento"}), 500


@bp.route("/create-mercadopago-subscription", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
@validate_with_schema(SubscriptionSchema, location="json")
def create_mercadopago_subscription():
    """Criar assinatura recorrente (preapproval) no Mercado Pago"""
    try:
        data = request.validated_data
        plan_id = data.get("plan_id")
        card_token = data.get("card_token")
        auto_recurring = data.get("auto_recurring", True)

        plan = BillingPlan.query.get_or_404(plan_id)
        if not plan.active:
            return jsonify({"error": "Plano inválido ou inativo"}), 400

        # Validar que é subscription (não pay-per-use)
        if plan.plan_type == "per_usage":
            return jsonify(
                {"error": "Preapproval disponível apenas para assinaturas"}
            ), 400

        amount = float(plan.monthly_fee)

        # Criar preapproval (assinatura recorrente)
        preapproval_data = {
            "payer_email": current_user.email,
            "back_url": url_for("payments.success", _external=True),
            "reason": f"Petitio - {plan.name}",
            "external_reference": f"sub_{current_user.id}_{plan.id}",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months",
                "transaction_amount": amount,
                "currency_id": "BRL",
            },
            "status": "pending",
        }

        result = mp_sdk.preapproval().create(preapproval_data)

        if result["status"] != 201:
            current_app.logger.error(f"Mercado Pago preapproval error: {result}")
            return jsonify({"error": "Erro ao criar assinatura"}), 500

        preapproval = result["response"]

        # Salvar assinatura no banco
        subscription = Subscription(
            user_id=current_user.id,
            plan_type=plan.plan_type,
            billing_period=billing_period,
            amount=Decimal(str(amount)),
            status="pending",
            gateway="mercadopago",
            gateway_subscription_id=preapproval["id"],
            gateway_customer_id=None,  # MP não tem customer_id como outros gateways
        )
        db.session.add(subscription)
        db.session.commit()

        # Auditoria: assinatura criada
        AuditManager.log_subscription_created(subscription, current_user)

        return jsonify(
            {
                "preapproval_url": preapproval["init_point"],
                "preapproval_id": preapproval["id"],
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao criar preapproval Mercado Pago: {str(e)}")
        return jsonify({"error": "Erro ao processar assinatura"}), 500


def _validate_mercadopago_webhook_signature(request_data, headers):
    """Valida a assinatura do webhook do Mercado Pago"""
    try:
        # Obter chave secreta
        webhook_secret = current_app.config.get("MERCADOPAGO_WEBHOOK_SECRET")
        if not webhook_secret:
            current_app.logger.warning("MERCADOPAGO_WEBHOOK_SECRET não configurado")
            return False

        # Extrair headers necessários
        x_signature = headers.get("x-signature")
        x_request_id = headers.get("x-request-id")

        if not x_signature or not x_request_id:
            current_app.logger.warning("Headers x-signature ou x-request-id ausentes")
            return False

        # Parse do x-signature: ts=1704908010,v1=signature
        try:
            parts = x_signature.split(",")
            ts = None
            signature = None

            for part in parts:
                if part.startswith("ts="):
                    ts = part.split("=", 1)[1]
                elif part.startswith("v1="):
                    signature = part.split("=", 1)[1]

            if not ts or not signature:
                current_app.logger.warning("Formato inválido do header x-signature")
                return False

        except Exception as e:
            current_app.logger.error(f"Erro ao parsear x-signature: {str(e)}")
            return False

        # Criar template para assinatura
        # id:[data.id];request-id:[x-request-id];ts:[ts];
        data_id = str(request_data.get("data", {}).get("id", "")).lower()
        template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

        # Calcular assinatura esperada usando HMAC-SHA256
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"), template.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Comparar assinaturas
        if hmac.compare_digest(signature, expected_signature):
            return True
        else:
            current_app.logger.warning("Assinatura do webhook inválida")
            return False

    except Exception as e:
        current_app.logger.error(f"Erro na validação da assinatura: {str(e)}")
        return False


@bp.route("/webhook/mercadopago", methods=["POST"])
@limiter.limit("100 per minute")
@validate_with_schema(WebhookSchema, location="json")
def mercadopago_webhook():
    """Webhook do Mercado Pago (pagamentos únicos e recorrentes)"""
    try:
        data = request.validated_data

        # Validar assinatura do webhook (camada adicional de segurança)
        if not _validate_mercadopago_webhook_signature(data, request.headers):
            current_app.logger.warning("Webhook Mercado Pago com assinatura inválida")
            return jsonify({"error": "Invalid signature"}), 401

        event_type = data.get("type")

        if event_type == "payment":
            # Pagamento único (PIX ou cartão)
            payment_id = data.get("data", {}).get("id")
            if payment_id:
                _handle_payment_webhook(payment_id)

        elif event_type == "preapproval":
            # Assinatura recorrente (preapproval)
            preapproval_id = data.get("data", {}).get("id")
            if preapproval_id:
                _handle_preapproval_webhook(preapproval_id)

        return jsonify({"received": True}), 200

    except Exception as e:
        current_app.logger.error(f"Erro no webhook Mercado Pago: {str(e)}")
        error_msg = format_error_for_user(e, "Erro ao processar webhook")
        return jsonify({"error": error_msg}), 500


def _handle_payment_webhook(payment_id):
    """Processa webhook de pagamento único"""
    # Buscar detalhes do pagamento
    payment_info = mp_sdk.payment().get(payment_id)
    payment_data = payment_info["response"]

    if payment_data["status"] == "approved":
        # Encontrar pagamento no banco
        payment = Payment.query.filter_by(gateway_payment_id=str(payment_id)).first()

        if payment and payment.status == "pending":
            old_status = payment.status
            payment.mark_as_paid()

            # Para pay-per-use, ativar plano imediatamente
            if payment.payment_type == "one_time":
                user = db.session.get(User, payment.user_id)
                user.billing_status = "active"
                db.session.commit()

            # Processar conversão de indicação (primeiro pagamento)
            _process_referral_conversion(payment.user_id, payment.id, payment.amount)

            # Auditoria: pagamento aprovado
            AuditManager.log_payment_completed(payment)

            current_app.logger.info(f"✅ Pagamento Mercado Pago aprovado: {payment_id}")

    elif payment_data["status"] in ["rejected", "cancelled"]:
        payment = Payment.query.filter_by(gateway_payment_id=str(payment_id)).first()
        if payment and payment.status == "pending":
            payment.status = "failed"
            db.session.commit()
            # Auditoria: pagamento falhou
            AuditManager.log_payment_failed(
                payment, f"Status: {payment_data['status']}"
            )


def _handle_preapproval_webhook(preapproval_id):
    """Processa webhook de preapproval (assinatura)"""
    # Buscar detalhes da assinatura
    preapproval_info = mp_sdk.preapproval().get(preapproval_id)
    preapproval_data = preapproval_info["response"]

    # Encontrar assinatura no banco
    subscription = Subscription.query.filter_by(
        gateway_subscription_id=str(preapproval_id)
    ).first()

    if not subscription:
        current_app.logger.warning(f"Preapproval não encontrado: {preapproval_id}")
        return

    old_status = subscription.status

    if preapproval_data["status"] == "authorized":
        # Assinatura aprovada - ativar
        subscription.status = "active"
        subscription.started_at = datetime.now(timezone.utc)

        # Calcular próxima renovação
        if subscription.billing_period == "monthly":
            subscription.renewal_date = datetime.now(timezone.utc) + timedelta(days=30)
        else:  # yearly
            subscription.renewal_date = datetime.now(timezone.utc) + timedelta(days=365)

        # Ativar usuário
        user = subscription.user
        user.billing_status = "active"

        db.session.commit()

        # Processar conversão de indicação (primeiro pagamento)
        _process_referral_conversion(subscription.user_id, None, subscription.price)

        # Auditoria: assinatura ativada
        AuditManager.log_subscription_activated(subscription)

        current_app.logger.info(f"✅ Assinatura Mercado Pago ativada: {preapproval_id}")

    elif preapproval_data["status"] == "cancelled":
        # Assinatura cancelada
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)

        # Desativar usuário se não tiver outras assinaturas ativas
        user = subscription.user
        active_subs = Subscription.query.filter_by(
            user_id=user.id, status="active"
        ).count()

        if active_subs == 0:
            user.billing_status = "inactive"

        db.session.commit()

        # Auditoria: assinatura cancelada
        AuditManager.log_subscription_cancelled(
            subscription, reason="Cancelamento via gateway"
        )

        current_app.logger.info(
            f"❌ Assinatura Mercado Pago cancelada: {preapproval_id}"
        )

    elif preapproval_data["status"] == "paused":
        # Assinatura pausada
        subscription.status = "paused"
        user = subscription.user
        user.billing_status = "inactive"

        db.session.commit()

        # Auditoria: status alterado
        AuditManager.log_subscription_status_change(
            subscription, old_status, "paused", "Pausada via gateway"
        )

        current_app.logger.warning(
            f"⏸️ Assinatura Mercado Pago pausada: {preapproval_id}"
        )

    elif preapproval_data["status"] == "expired":
        # Assinatura expirada
        subscription.status = "expired"
        user = subscription.user
        user.billing_status = "inactive"

        db.session.commit()

        # Auditoria: status alterado
        AuditManager.log_subscription_status_change(
            subscription, old_status, "expired", "Expirada"
        )

        current_app.logger.warning(
            f"⏰ Assinatura Mercado Pago expirada: {preapproval_id}"
        )

    else:
        current_app.logger.info(
            f"ℹ️ Status de preapproval não tratado: {preapproval_data['status']} para {preapproval_id}"
        )

    return jsonify({"received": True}), 200


@bp.route("/my-subscription")
@login_required
def my_subscription():
    """Página de gerenciamento de assinatura"""
    subscription = (
        Subscription.query.filter_by(user_id=current_user.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )

    payments = (
        Payment.query.filter_by(user_id=current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "payments/my_subscription.html",
        subscription=subscription,
        payments=payments,
        plans=BillingPlan.query.filter_by(active=True).all(),
    )


@bp.route("/cancel-subscription", methods=["POST"])
@login_required
@limiter.limit("3 per hour")
def cancel_subscription():
    """Cancelar assinatura"""
    try:
        subscription = Subscription.query.filter_by(
            user_id=current_user.id, status="active"
        ).first()

        if not subscription:
            return jsonify({"error": "Assinatura não encontrada"}), 404

        immediate = request.json.get("immediate", False) if request.is_json else False
        reason = (
            request.json.get("reason", "Solicitado pelo usuário")
            if request.is_json
            else "Solicitado pelo usuário"
        )

        subscription.cancel(immediate=immediate)

        # Auditoria: assinatura cancelada pelo usuário
        AuditManager.log_subscription_cancelled(
            subscription, reason=reason, immediate=immediate
        )

        flash("Assinatura cancelada com sucesso", "success")
        return jsonify({"success": True})
    except Exception as e:
        error_msg = format_error_for_user(e, "Erro ao cancelar assinatura")
        return jsonify({"error": error_msg}), 400


@bp.route("/success")
@login_required
def success():
    """Página de sucesso após pagamento"""
    return render_template("payments/success.html")


@bp.route("/payment-status/<int:payment_id>")
@login_required
def payment_status(payment_id):
    """Verificar status do pagamento"""
    payment = Payment.query.get_or_404(payment_id)

    if payment.user_id != current_user.id:
        abort(403)

    return jsonify(payment.to_dict())


@bp.route("/cancellation-policy")
def cancellation_policy():
    """Página da política de cancelamento e reembolso"""
    return render_template("payments/cancellation_policy.html")
