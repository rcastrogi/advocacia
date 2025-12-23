"""
Rotas de pagamento - Mercado Pago Único
PIX: Pagamentos únicos instantâneos
Preapprovals: Assinaturas recorrentes automáticas
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta
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

from app import db
from app.models import BillingPlan, Payment, Subscription, User
from app.payments import bp

# Configurar Mercado Pago
mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = mercadopago.SDK(mp_access_token) if mp_access_token else None


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

    if billing_period not in ["monthly", "yearly"]:
        flash("Período de cobrança inválido", "error")
        return redirect(url_for("payments.plans"))

    # Para planos mensais, usar monthly_fee; para yearly, calcular baseado no monthly_fee
    if billing_period == "monthly":
        amount = float(plan.monthly_fee)
    else:  # yearly
        amount = float(plan.monthly_fee) * 12
    amount = plan[billing_period]

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
    )


@bp.route("/create-pix-payment", methods=["POST"])
@login_required
def create_pix_payment():
    """Criar pagamento PIX via Mercado Pago (apenas para pay-per-use)"""
    try:
        data = request.get_json()
        plan_slug = data.get("plan_slug")
        billing_period = data.get("billing_period")

        plan = BillingPlan.query.filter_by(slug=plan_slug, active=True).first()
        if not plan:
            return jsonify({"error": "Plano inválido"}), 400

        # Validar que é pay-per-use (não subscription)
        if plan.plan_type != "per_usage":
            return jsonify(
                {"error": "PIX disponível apenas para planos pay-per-use"}
            ), 400

        # Para planos mensais, usar monthly_fee; para yearly, calcular baseado no monthly_fee
        if billing_period == "monthly":
            amount = float(plan.monthly_fee)
        else:  # yearly
            amount = float(plan.monthly_fee) * 12

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
            pix_expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        db.session.add(payment)
        db.session.commit()

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
def create_mercadopago_subscription():
    """Criar assinatura recorrente (preapproval) no Mercado Pago"""
    try:
        data = request.get_json()
        plan_slug = data.get("plan_slug")
        billing_period = data.get("billing_period")

        plan = BillingPlan.query.filter_by(slug=plan_slug, active=True).first()
        if not plan:
            return jsonify({"error": "Plano inválido"}), 400

        # Validar que é subscription (não pay-per-use)
        if plan.plan_type == "per_usage":
            return jsonify(
                {"error": "Preapproval disponível apenas para assinaturas"}
            ), 400

        # Para planos mensais, usar monthly_fee; para yearly, calcular baseado no monthly_fee
        if billing_period == "monthly":
            amount = float(plan.monthly_fee)
        else:  # yearly
            amount = float(plan.monthly_fee) * 12

        # Criar preapproval (assinatura recorrente)
        preapproval_data = {
            "payer_email": current_user.email,
            "back_url": url_for("payments.success", _external=True),
            "reason": f"Petitio - {plan.name} ({billing_period})",
            "external_reference": f"sub_{current_user.id}_{plan.id}_{billing_period}",
            "auto_recurring": {
                "frequency": 1,
                "frequency_type": "months" if billing_period == "monthly" else "years",
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
            gateway_customer_id=None,  # MP não tem customer_id como Stripe
            started_at=None,  # Será definido quando aprovado
            renewal_date=None,  # Será definido quando aprovado
        )
        db.session.add(subscription)
        db.session.commit()

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
def mercadopago_webhook():
    """Webhook do Mercado Pago (pagamentos únicos e recorrentes)"""
    try:
        # Validar assinatura do webhook
        data = request.get_json()
        if not _validate_mercadopago_webhook_signature(data, request.headers):
            current_app.logger.warning("Webhook Mercado Pago com assinatura inválida")
            return jsonify({"error": "Invalid signature"}), 401

        event_type = data.get("type")

        if event_type == "payment":
            # Pagamento único (PIX ou cartão)
            payment_id = data["data"]["id"]
            _handle_payment_webhook(payment_id)

        elif event_type == "preapproval":
            # Assinatura recorrente (preapproval)
            preapproval_id = data["data"]["id"]
            _handle_preapproval_webhook(preapproval_id)

        return jsonify({"received": True}), 200

    except Exception as e:
        current_app.logger.error(f"Erro no webhook Mercado Pago: {str(e)}")
        return jsonify({"error": str(e)}), 500


def _handle_payment_webhook(payment_id):
    """Processa webhook de pagamento único"""
    # Buscar detalhes do pagamento
    payment_info = mp_sdk.payment().get(payment_id)
    payment_data = payment_info["response"]

    if payment_data["status"] == "approved":
        # Encontrar pagamento no banco
        payment = Payment.query.filter_by(gateway_payment_id=str(payment_id)).first()

        if payment and payment.status == "pending":
            payment.mark_as_paid()

            # Para pay-per-use, ativar plano imediatamente
            if payment.payment_type == "one_time":
                user = User.query.get(payment.user_id)
                user.billing_status = "active"
                db.session.commit()

            current_app.logger.info(f"✅ Pagamento Mercado Pago aprovado: {payment_id}")


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

    if preapproval_data["status"] == "authorized":
        # Assinatura aprovada - ativar
        subscription.status = "active"
        subscription.started_at = datetime.utcnow()

        # Calcular próxima renovação
        if subscription.billing_period == "monthly":
            subscription.renewal_date = datetime.utcnow() + timedelta(days=30)
        else:  # yearly
            subscription.renewal_date = datetime.utcnow() + timedelta(days=365)

        # Ativar usuário
        user = subscription.user
        user.billing_status = "active"

        db.session.commit()
        current_app.logger.info(f"✅ Assinatura Mercado Pago ativada: {preapproval_id}")

    elif preapproval_data["status"] == "cancelled":
        # Assinatura cancelada
        subscription.status = "cancelled"

        # Desativar usuário se não tiver outras assinaturas ativas
        user = subscription.user
        active_subs = Subscription.query.filter_by(
            user_id=user.id, status="active"
        ).count()

        if active_subs == 0:
            user.billing_status = "inactive"

        db.session.commit()
        current_app.logger.info(
            f"❌ Assinatura Mercado Pago cancelada: {preapproval_id}"
        )

    elif preapproval_data["status"] == "paused":
        # Assinatura pausada
        subscription.status = "paused"
        user = subscription.user
        user.billing_status = "inactive"

        db.session.commit()
        current_app.logger.warning(
            f"⏸️ Assinatura Mercado Pago pausada: {preapproval_id}"
        )

    elif preapproval_data["status"] == "expired":
        # Assinatura expirada
        subscription.status = "expired"
        user = subscription.user
        user.billing_status = "inactive"

        db.session.commit()
        current_app.logger.warning(
            f"⏰ Assinatura Mercado Pago expirada: {preapproval_id}"
        )

    else:
        current_app.logger.info(
            f"ℹ️ Status de preapproval não tratado: {preapproval_data['status']} para {preapproval_id}"
        )

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        user_id = session["metadata"]["user_id"]
        plan_type = session["metadata"]["plan_type"]
        billing_period = session["metadata"]["billing_period"]

        # Criar subscription
        subscription = Subscription(
            user_id=user_id,
            plan_type=plan_type,
            billing_period=billing_period,
            amount=Decimal(str(session["amount_total"] / 100)),
            status="active",
            gateway="stripe",
            gateway_subscription_id=session["subscription"],
            gateway_customer_id=session["customer"],
        )
        db.session.add(subscription)

        # Atualizar usuário
        user = User.query.get(user_id)
        user.billing_status = "active"
        user.stripe_customer_id = session["customer"]

        db.session.commit()

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
        plans=PLANS,
    )


@bp.route("/cancel-subscription", methods=["POST"])
@login_required
def cancel_subscription():
    """Cancelar assinatura"""
    subscription = Subscription.query.filter_by(
        user_id=current_user.id, status="active"
    ).first()

    if not subscription:
        return jsonify({"error": "Assinatura não encontrada"}), 404

    immediate = request.json.get("immediate", False)
    subscription.cancel(immediate=immediate)

    flash("Assinatura cancelada com sucesso", "success")
    return jsonify({"success": True})


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
