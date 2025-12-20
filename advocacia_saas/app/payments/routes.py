"""
Rotas de pagamento - Mercado Pago + Stripe
"""

import os
from datetime import datetime, timedelta
from decimal import Decimal

import mercadopago
import stripe
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

# Configurar gateways (lazy initialization para evitar erros se não configurado)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_dummy")
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
        plan_type=plan_type,
        plan_name=plan["name"],
        billing_period=billing_period,
        amount=amount,
    )


@bp.route("/create-pix-payment", methods=["POST"])
@login_required
def create_pix_payment():
    """Criar pagamento PIX via Mercado Pago"""
    try:
        data = request.get_json()
        plan_slug = data.get("plan_slug")
        billing_period = data.get("billing_period")

        plan = BillingPlan.query.filter_by(slug=plan_slug, active=True).first()
        if not plan:
            return jsonify({"error": "Plano inválido"}), 400

        # Para planos mensais, usar monthly_fee; para yearly, calcular baseado no monthly_fee
        if billing_period == "monthly":
            amount = float(plan.monthly_fee)
        else:  # yearly
            amount = float(plan.monthly_fee) * 12

        # Criar pagamento no Mercado Pago
        payment_data = {
            "transaction_amount": amount,
            "description": f"Assinatura Petitio - {plan.name} ({billing_period})",
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
            payment_type="subscription",
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

        # Criar subscription pendente
        period_end = datetime.utcnow()
        if billing_period == "monthly":
            period_end += timedelta(days=30)
        else:
            period_end += timedelta(days=365)

        subscription = Subscription(
            user_id=current_user.id,
            plan_type=plan_type,
            billing_period=billing_period,
            amount=Decimal(str(amount)),
            status="pending",
            current_period_start=datetime.utcnow(),
            current_period_end=period_end,
            gateway="mercadopago",
            gateway_payment_id=str(payment_response["id"]),
        )
        db.session.add(subscription)
        payment.subscription = subscription

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


@bp.route("/create-stripe-checkout", methods=["POST"])
@login_required
def create_stripe_checkout():
    """Criar sessão de checkout Stripe (cartão internacional)"""
    try:
        data = request.get_json()
        plan_slug = data.get("plan_slug")
        billing_period = data.get("billing_period")

        plan = BillingPlan.query.filter_by(slug=plan_slug, active=True).first()
        if not plan:
            return jsonify({"error": "Plano inválido"}), 400

        # Para planos mensais, usar monthly_fee; para yearly, calcular baseado no monthly_fee
        if billing_period == "monthly":
            amount = int(float(plan.monthly_fee) * 100)  # Centavos
        else:  # yearly
            amount = int(float(plan.monthly_fee) * 12 * 100)  # Centavos

        # Criar sessão de checkout
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "brl",
                        "product_data": {
                            "name": f"Petitio - {plan.name}",
                            "description": f"Assinatura {billing_period}",
                        },
                        "unit_amount": amount,
                        "recurring": {
                            "interval": "month"
                            if billing_period == "monthly"
                            else "year"
                        },
                    },
                    "quantity": 1,
                }
            ],
            mode="subscription",
            success_url=url_for("payments.success", _external=True)
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("payments.plans", _external=True),
            customer_email=current_user.email,
            metadata={
                "user_id": current_user.id,
                "plan_type": plan_type,
                "billing_period": billing_period,
            },
        )

        return jsonify({"checkout_url": session.url})

    except Exception as e:
        current_app.logger.error(f"Erro ao criar checkout Stripe: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento"}), 500


@bp.route("/webhook/mercadopago", methods=["POST"])
def mercadopago_webhook():
    """Webhook do Mercado Pago"""
    try:
        data = request.get_json()

        if data.get("type") == "payment":
            payment_id = data["data"]["id"]

            # Buscar detalhes do pagamento
            payment_info = mp_sdk.payment().get(payment_id)
            payment_data = payment_info["response"]

            if payment_data["status"] == "approved":
                # Encontrar pagamento no banco
                payment = Payment.query.filter_by(
                    gateway_payment_id=str(payment_id)
                ).first()

                if payment and payment.status == "pending":
                    payment.mark_as_paid()

                    # Ativar assinatura
                    if payment.subscription:
                        payment.subscription.status = "active"
                        payment.subscription.gateway_subscription_id = str(payment_id)
                        db.session.commit()

                        # Atualizar status do usuário
                        user = User.query.get(payment.user_id)
                        user.billing_status = "active"
                        db.session.commit()

        return jsonify({"received": True}), 200

    except Exception as e:
        current_app.logger.error(f"Erro no webhook Mercado Pago: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    """Webhook do Stripe"""
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

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
