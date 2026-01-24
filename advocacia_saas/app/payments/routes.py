"""
Payments Routes - Refatorado para usar Services
"""

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import limiter
from app.decorators import validate_with_schema
from app.payments import bp
from app.payments.services import (
    BalanceDashboardService,
    BalanceDepositService,
    PIXPaymentService,
    SubscriptionService,
    WebhookProcessorService,
    WebhookSecurityService,
)
from app.schemas import PaymentSchema, SubscriptionSchema, WebhookSchema
from app.utils.error_messages import format_error_for_user


# ===========================================================================
# PLANOS E ASSINATURAS
# ===========================================================================


@bp.route("/plans")
@login_required
def plans():
    """Página de planos"""
    current_subscription = SubscriptionService.get_user_subscription(current_user)

    return render_template(
        "payments/plans.html",
        plans=SubscriptionService.get_plans(),
        current_subscription=current_subscription,
    )


@bp.route("/subscribe/<plan_slug>/<billing_period>")
@login_required
def subscribe(plan_slug, billing_period):
    """Iniciar processo de assinatura"""
    # Validar requisição
    result, error = SubscriptionService.validate_subscription_request(
        plan_slug, billing_period
    )

    if error:
        flash(error, "error")
        return redirect(url_for("payments.plans"))

    # Verificar assinatura existente
    existing = SubscriptionService.get_user_subscription(current_user)
    if existing:
        flash("Você já possui uma assinatura ativa", "warning")
        return redirect(url_for("payments.my_subscription"))

    return render_template(
        "payments/checkout.html",
        plan_slug=plan_slug,
        plan_type=result["plan"].plan_type,
        plan_name=result["plan"].name,
        billing_period=billing_period,
        amount=result["amount"],
        period_label=result["period_label"],
    )


# ===========================================================================
# PAGAMENTOS PIX
# ===========================================================================


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
        billing_period = data.get("billing_period", "1m")

        # Buscar plano se informado
        plan = None
        if plan_id:
            from app.payments.repository import BillingPlanPaymentRepository
            plan = BillingPlanPaymentRepository.get_by_id(plan_id)

        result, error = PIXPaymentService.create_payment(
            current_user, amount, plan, billing_period
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({"success": True, **result})

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erro ao criar pagamento PIX: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento"}), 500


# ===========================================================================
# ASSINATURAS RECORRENTES
# ===========================================================================


@bp.route("/create-mercadopago-subscription", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
@validate_with_schema(SubscriptionSchema, location="json")
def create_mercadopago_subscription():
    """Criar assinatura recorrente (preapproval) no Mercado Pago"""
    try:
        data = request.validated_data
        plan_id = data.get("plan_id")
        billing_period = data.get("billing_period", "monthly")

        from app.payments.repository import BillingPlanPaymentRepository
        plan = BillingPlanPaymentRepository.get_by_id(plan_id)

        if not plan or not plan.active:
            return jsonify({"error": "Plano inválido ou inativo"}), 400

        result, error = SubscriptionService.create_subscription(
            current_user, plan, billing_period
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify(result)

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erro ao criar preapproval: {str(e)}")
        return jsonify({"error": "Erro ao processar assinatura"}), 500


# ===========================================================================
# WEBHOOK MERCADO PAGO
# ===========================================================================


@bp.route("/webhook/mercadopago", methods=["POST"])
@limiter.limit("100 per minute")
@validate_with_schema(WebhookSchema, location="json")
def mercadopago_webhook():
    """Webhook do Mercado Pago (pagamentos únicos e recorrentes)"""
    try:
        data = request.validated_data

        # Validar assinatura
        if not WebhookSecurityService.validate_mercadopago_signature(data, request.headers):
            from flask import current_app
            current_app.logger.warning("Webhook Mercado Pago com assinatura inválida")
            return jsonify({"error": "Invalid signature"}), 401

        event_type = data.get("type")

        if event_type == "payment":
            payment_id = data.get("data", {}).get("id")
            if payment_id:
                WebhookProcessorService.process_payment_webhook(str(payment_id))

        elif event_type == "preapproval":
            preapproval_id = data.get("data", {}).get("id")
            if preapproval_id:
                WebhookProcessorService.process_preapproval_webhook(str(preapproval_id))

        return jsonify({"received": True}), 200

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erro no webhook Mercado Pago: {str(e)}")
        error_msg = format_error_for_user(e, "Erro ao processar webhook")
        return jsonify({"error": error_msg}), 500


# ===========================================================================
# GERENCIAMENTO DE ASSINATURA
# ===========================================================================


@bp.route("/my-subscription")
@login_required
def my_subscription():
    """Página de gerenciamento de assinatura"""
    from app.payments.repository import BillingPlanPaymentRepository, PaymentRepository

    subscription = SubscriptionService.get_latest_subscription(current_user)
    payments = PaymentRepository.get_user_payments(current_user.id, limit=10)

    return render_template(
        "payments/my_subscription.html",
        subscription=subscription,
        payments=payments,
        plans=BillingPlanPaymentRepository.get_active_plans(),
    )


@bp.route("/cancel-subscription", methods=["POST"])
@login_required
@limiter.limit("3 per hour")
def cancel_subscription():
    """Cancelar assinatura"""
    try:
        immediate = request.json.get("immediate", False) if request.is_json else False
        reason = (
            request.json.get("reason", "Solicitado pelo usuário")
            if request.is_json
            else "Solicitado pelo usuário"
        )

        success, error = SubscriptionService.cancel_subscription(
            current_user, immediate=immediate, reason=reason
        )

        if not success:
            return jsonify({"error": error}), 404

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
    from app.payments.repository import PaymentRepository

    payment = PaymentRepository.get_by_id(payment_id)
    if not payment:
        abort(404)

    if payment.user_id != current_user.id:
        abort(403)

    return jsonify(payment.to_dict())


@bp.route("/cancellation-policy")
def cancellation_policy():
    """Página da política de cancelamento e reembolso"""
    return render_template("payments/cancellation_policy.html")


# ===========================================================================
# SISTEMA DE SALDO PARA PETIÇÕES (PAY PER USE)
# ===========================================================================


@bp.route("/balance")
@login_required
def balance_dashboard():
    """Dashboard de saldo do usuário para petições"""
    balance_info = BalanceDashboardService.get_balance_info(current_user)

    return render_template(
        "payments/balance_dashboard.html",
        balance=balance_info["balance"],
        transactions=balance_info["transactions"],
    )


@bp.route("/balance/deposit")
@login_required
def balance_deposit():
    """Página para adicionar saldo"""
    suggested_amounts = [50, 100, 200, 500, 1000]

    return render_template(
        "payments/balance_deposit.html",
        suggested_amounts=suggested_amounts,
    )


@bp.route("/balance/create-pix", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def create_balance_pix():
    """Criar pagamento PIX para adicionar saldo"""
    try:
        from decimal import Decimal

        data = request.get_json()
        amount = Decimal(str(data.get("amount", 0)))

        result, error = BalanceDepositService.create_pix_deposit(current_user, amount)

        if error:
            return jsonify({"error": error}), 400 if "mínimo" in error or "máximo" in error else 500

        return jsonify({"success": True, **result})

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erro ao criar PIX para depósito: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento"}), 500


@bp.route("/balance/history")
@login_required
def balance_history():
    """Histórico completo de transações de saldo"""
    page = request.args.get("page", 1, type=int)

    transactions = BalanceDashboardService.get_transactions_paginated(
        current_user, page=page, per_page=20
    )

    return render_template(
        "payments/balance_history.html",
        transactions=transactions,
    )
