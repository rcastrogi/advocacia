from datetime import datetime, timedelta
from decimal import Decimal

import stripe
from flask import (
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.checkout import bp
from app.models import BillingPlan, Payment, User, UserPlan


def get_stripe_client():
    """Initialize and return Stripe client with API key"""
    stripe.api_key = current_app.config.get("STRIPE_SECRET_KEY")
    return stripe


@bp.route("/<int:plan_id>")
@login_required
def create_checkout_session(plan_id):
    """Create a Stripe Checkout session for the selected plan"""
    plan = BillingPlan.query.get_or_404(plan_id)

    if not plan.is_active:
        flash("Este plano não está mais disponível.", "error")
        return redirect(url_for("main.index"))

    # Initialize Stripe
    stripe_client = get_stripe_client()

    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe_client.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                metadata={
                    "user_id": current_user.id,
                    "oab_number": current_user.oab_number or "",
                },
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()

        # Check if user has an active Stripe subscription for upgrade
        existing_subscription = None
        current_plan = current_user.get_active_plan()

        # Apply proration for:
        # 1. Limited → Unlimited upgrades
        # 2. Unlimited → Unlimited upgrades (different periods)
        should_apply_proration = False

        if current_plan:
            if (current_plan.plan.plan_type in ['limited', 'flat_monthly'] and 
                plan.plan_type == 'unlimited'):
                # Limited to unlimited upgrade
                should_apply_proration = True
            elif (current_plan.plan.plan_type == 'unlimited' and 
                  plan.plan_type == 'unlimited' and
                  plan.monthly_fee > current_plan.plan.monthly_fee):
                # Unlimited to unlimited upgrade (higher price)
                should_apply_proration = True

        if should_apply_proration:
            # Look for active Stripe subscription
            try:
                subscriptions = stripe_client.Subscription.list(
                    customer=current_user.stripe_customer_id,
                    status='active',
                    limit=1
                )
                if subscriptions.data:
                    existing_subscription = subscriptions.data[0]
            except stripe.error.StripeError:
                # If there's an error retrieving subscription, continue with new subscription
                pass

        # Determine pricing mode and handle upgrades
        if plan.is_per_usage:
            # Pay-per-use: One-time payment for initial setup
            line_items = [
                {
                    "price_data": {
                        "currency": "brl",
                        "product_data": {
                            "name": f"{plan.name} - Taxa de Adesão",
                            "description": f"Plano por uso - pague apenas pelo que utilizar",
                        },
                        "unit_amount": 0,  # Free to start, pay per petition
                    },
                    "quantity": 1,
                }
            ]
            mode = "payment"
        else:
            # Monthly subscription
            if existing_subscription and current_plan:
                # This is an upgrade - calculate proration
                try:
                    # Get current subscription item
                    current_item = existing_subscription.items.data[0]

                    # Calculate proration for upgrade
                    proration = stripe_client.Invoice.upcoming(
                        customer=current_user.stripe_customer_id,
                        subscription=existing_subscription.id,
                        subscription_items=[{
                            'id': current_item.id,
                            'price_data': {
                                'currency': 'brl',
                                'product_data': {
                                    'name': plan.name,
                                    'description': plan.description or f"Plano {plan.name} - Mensal",
                                },
                                'unit_amount': int(float(plan.monthly_fee) * 100),
                                'recurring': {'interval': 'month'},
                            },
                        }],
                        subscription_proration_behavior='always_invoice',
                    )

                    # Create checkout session for upgrade with proration
                    checkout_session = stripe_client.checkout.Session.create(
                        customer=current_user.stripe_customer_id,
                        payment_method_types=["card"],
                        line_items=[{
                            "price": proration.lines.data[-1].price.id,  # Use the prorated price
                            "quantity": 1,
                        }],
                        mode="subscription",
                        subscription_data={
                            "items": [{
                                'price_data': {
                                    'currency': 'brl',
                                    'product_data': {
                                        'name': plan.name,
                                        'description': plan.description or f"Plano {plan.name} - Mensal",
                                    },
                                    'unit_amount': int(float(plan.monthly_fee) * 100),
                                    'recurring': {'interval': 'month'},
                                },
                            }],
                            "proration_behavior": "always_invoice",
                        },
                        success_url=current_app.config.get("STRIPE_SUCCESS_URL")
                        + "?session_id={CHECKOUT_SESSION_ID}",
                        cancel_url=current_app.config.get("STRIPE_CANCEL_URL"),
                        metadata={
                            "user_id": current_user.id,
                            "plan_id": plan.id,
                            "upgrade": "true",
                            "old_plan_id": current_plan.plan.id,
                        },
                        allow_promotion_codes=True,
                        billing_address_collection="required",
                    )

                except stripe.error.StripeError as e:
                    # If proration fails, fall back to new subscription
                    current_app.logger.warning(f"Proration failed, creating new subscription: {str(e)}")
                    existing_subscription = None

            if not existing_subscription:
                # New subscription or fallback
                line_items = [
                    {
                        "price_data": {
                            "currency": "brl",
                            "product_data": {
                                "name": plan.name,
                                "description": plan.description
                                or f"Plano {plan.name} - Mensal",
                            },
                            "unit_amount": int(
                                float(plan.monthly_fee) * 100
                            ),  # Convert to cents
                            "recurring": {"interval": "month"},
                        },
                        "quantity": 1,
                    }
                ]
                mode = "subscription"

                # Create Checkout Session
                checkout_session = stripe_client.checkout.Session.create(
                    customer=current_user.stripe_customer_id,
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode=mode,
                    success_url=current_app.config.get("STRIPE_SUCCESS_URL")
                    + "?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url=current_app.config.get("STRIPE_CANCEL_URL"),
                    metadata={
                        "user_id": current_user.id,
                        "plan_id": plan.id,
                    },
                    allow_promotion_codes=True,
                    billing_address_collection="required",
                )

        # Store session ID in user session for later verification
        session["pending_checkout_session_id"] = checkout_session.id
        session["pending_plan_id"] = plan.id

        # Update user billing status
        current_user.billing_status = "pending_payment"
        db.session.commit()

        # Redirect to Stripe Checkout
        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error: {str(e)}")
        flash(f"Erro ao processar pagamento: {str(e)}", "error")
        return redirect(url_for("billing.portal"))
    except Exception as e:
        current_app.logger.error(f"Checkout error: {str(e)}")
        flash("Ocorreu um erro ao processar sua solicitação. Tente novamente.", "error")
        return redirect(url_for("billing.portal"))


@bp.route("/success")
@login_required
def checkout_success():
    """Handle successful checkout - verify and activate plan"""
    session_id = request.args.get("session_id")

    if not session_id:
        flash("Sessão de pagamento inválida.", "error")
        return redirect(url_for("main.dashboard"))

    stripe_client = get_stripe_client()

    try:
        # Retrieve the session to verify payment
        checkout_session = stripe_client.checkout.Session.retrieve(session_id)

        if checkout_session.payment_status == "paid":
            plan_id = session.get("pending_plan_id") or int(
                checkout_session.metadata.get("plan_id")
            )
            plan = BillingPlan.query.get(plan_id)

            if not plan:
                flash("Plano não encontrado.", "error")
                return redirect(url_for("main.dashboard"))

            # Check if plan already activated (prevent duplicate)
            existing_plan = UserPlan.query.filter_by(
                user_id=current_user.id, plan_id=plan.id, is_current=True
            ).first()

            if not existing_plan:
                # Deactivate any existing current plan
                UserPlan.query.filter_by(
                    user_id=current_user.id, is_current=True
                ).update({"is_current": False})

                # Create new active plan
                user_plan = UserPlan(
                    user_id=current_user.id,
                    plan_id=plan.id,
                    status="active",
                    started_at=datetime.utcnow(),
                    renewal_date=datetime.utcnow() + timedelta(days=30)
                    if not plan.is_per_usage
                    else None,
                    is_current=True,
                )
                db.session.add(user_plan)

                # Record payment
                payment = Payment(
                    user_id=current_user.id,
                    invoice_id=None,  # Create invoice later if needed
                    amount=Decimal(str(checkout_session.amount_total / 100)),
                    stripe_customer_id=checkout_session.customer,
                    stripe_checkout_session_id=session_id,
                    stripe_payment_intent_id=checkout_session.payment_intent,
                    stripe_subscription_id=checkout_session.subscription
                    if checkout_session.mode == "subscription"
                    else None,
                    payment_status="completed",
                    method=checkout_session.payment_method_types[0]
                    if checkout_session.payment_method_types
                    else "card",
                    paid_at=datetime.utcnow(),
                )
                db.session.add(payment)

                # Update user billing status
                current_user.billing_status = "active"
                db.session.commit()

                # Clear session data
                session.pop("pending_checkout_session_id", None)
                session.pop("pending_plan_id", None)

                flash(
                    f"✅ Pagamento confirmado! Plano {plan.name} ativado com sucesso.",
                    "success",
                )
            else:
                flash("Este plano já está ativo na sua conta.", "info")

            return redirect(url_for("billing.portal"))
        else:
            flash(
                "Pagamento ainda não foi confirmado. Aguarde alguns instantes.",
                "warning",
            )
            return redirect(url_for("billing.portal"))

    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe verification error: {str(e)}")
        flash("Erro ao verificar pagamento. Entre em contato com o suporte.", "error")
        return redirect(url_for("billing.portal"))


@bp.route("/cancel")
@login_required
def checkout_cancel():
    """Handle cancelled checkout"""
    # Clear any pending session data
    session.pop("pending_checkout_session_id", None)
    session.pop("pending_plan_id", None)

    flash("Pagamento cancelado. Você pode tentar novamente a qualquer momento.", "info")
    return redirect(url_for("main.index"))


@bp.route("/customer-portal")
@login_required
def customer_portal():
    """Redirect to Stripe Customer Portal for subscription management"""
    if not current_user.stripe_customer_id:
        flash("Você ainda não possui uma assinatura ativa.", "warning")
        return redirect(url_for("billing.portal"))

    stripe_client = get_stripe_client()

    try:
        portal_session = stripe_client.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for("billing.portal", _external=True),
        )
        return redirect(portal_session.url, code=303)
    except stripe.error.StripeError as e:
        current_app.logger.error(f"Portal creation error: {str(e)}")
        flash("Erro ao acessar portal de assinaturas.", "error")
        return redirect(url_for("billing.portal"))


@bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """
    Handle Stripe webhook events for automatic payment processing.
    This endpoint receives real-time updates from Stripe about payment status.

    Important: Configure this URL in your Stripe Dashboard:
    https://dashboard.stripe.com/webhooks
    """
    stripe_client = get_stripe_client()
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    if not webhook_secret:
        current_app.logger.warning("STRIPE_WEBHOOK_SECRET not configured")
        return {"status": "error", "message": "Webhook secret not configured"}, 500

    try:
        # Verify webhook signature
        event = stripe_client.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        current_app.logger.error("Invalid webhook payload")
        return {"status": "error", "message": "Invalid payload"}, 400
    except stripe.error.SignatureVerificationError:
        current_app.logger.error("Invalid webhook signature")
        return {"status": "error", "message": "Invalid signature"}, 400

    # Handle different event types
    event_type = event["type"]
    data = event["data"]["object"]

    current_app.logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(data)
        elif event_type == "payment_intent.succeeded":
            _handle_payment_succeeded(data)
        elif event_type == "payment_intent.payment_failed":
            _handle_payment_failed(data)
        elif event_type == "customer.subscription.created":
            _handle_subscription_created(data)
        elif event_type == "customer.subscription.updated":
            _handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(data)
        elif event_type == "invoice.paid":
            _handle_invoice_paid(data)
        elif event_type == "invoice.payment_failed":
            _handle_invoice_failed(data)
        else:
            current_app.logger.info(f"Unhandled event type: {event_type}")

    except Exception as e:
        current_app.logger.error(f"Error processing webhook {event_type}: {str(e)}")
        return {"status": "error", "message": str(e)}, 500

    return {"status": "success"}, 200


def _handle_checkout_completed(session):
    """Process completed checkout session"""
    user_id = int(session.get("metadata", {}).get("user_id", 0))
    plan_id = int(session.get("metadata", {}).get("plan_id", 0))

    if not user_id or not plan_id:
        current_app.logger.warning(
            f"Missing metadata in checkout session: {session.id}"
        )
        return

    user = User.query.get(user_id)
    plan = BillingPlan.query.get(plan_id)

    if not user or not plan:
        current_app.logger.error(f"User {user_id} or Plan {plan_id} not found")
        return

    # Check if already processed
    existing = Payment.query.filter_by(stripe_checkout_session_id=session.id).first()

    if existing:
        current_app.logger.info(f"Checkout {session.id} already processed")
        return

    # Deactivate existing plans
    UserPlan.query.filter_by(user_id=user_id, is_current=True).update(
        {"is_current": False}
    )

    # Create new plan
    user_plan = UserPlan(
        user_id=user_id,
        plan_id=plan_id,
        status="active",
        started_at=datetime.utcnow(),
        renewal_date=datetime.utcnow() + timedelta(days=30)
        if not plan.is_per_usage
        else None,
        is_current=True,
    )
    db.session.add(user_plan)

    # Record payment
    payment = Payment(
        user_id=user_id,
        invoice_id=None,
        amount=Decimal(str(session.amount_total / 100))
        if session.amount_total
        else Decimal("0.00"),
        stripe_customer_id=session.customer,
        stripe_checkout_session_id=session.id,
        stripe_payment_intent_id=session.payment_intent,
        stripe_subscription_id=session.subscription,
        payment_status="completed",
        method=session.payment_method_types[0]
        if session.payment_method_types
        else "card",
        paid_at=datetime.utcnow(),
        webhook_received_at=datetime.utcnow(),
    )
    db.session.add(payment)

    # Update user status
    user.billing_status = "active"

    db.session.commit()
    current_app.logger.info(f"✅ Plan {plan.name} activated for user {user.email}")


def _handle_payment_succeeded(payment_intent):
    """Handle successful payment"""
    payment = Payment.query.filter_by(
        stripe_payment_intent_id=payment_intent.id
    ).first()

    if payment:
        payment.payment_status = "completed"
        payment.webhook_received_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(f"✅ Payment {payment_intent.id} marked as completed")


def _handle_payment_failed(payment_intent):
    """Handle failed payment"""
    payment = Payment.query.filter_by(
        stripe_payment_intent_id=payment_intent.id
    ).first()

    if payment:
        payment.payment_status = "failed"
        payment.webhook_received_at = datetime.utcnow()

        # Update user billing status
        user = payment.user
        user.billing_status = "delinquent"

        db.session.commit()
        current_app.logger.warning(
            f"❌ Payment {payment_intent.id} failed for user {user.email}"
        )


def _handle_subscription_created(subscription):
    """Handle new subscription creation"""
    current_app.logger.info(f"Subscription created: {subscription.id}")


def _handle_subscription_updated(subscription):
    """Handle subscription updates (renewals, changes)"""
    current_app.logger.info(f"Subscription updated: {subscription.id}")


def _handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    payment = Payment.query.filter_by(stripe_subscription_id=subscription.id).first()

    if payment:
        user = payment.user
        user.billing_status = "inactive"

        # Deactivate user plans
        UserPlan.query.filter_by(user_id=user.id, is_current=True).update(
            {"is_current": False, "status": "cancelled"}
        )

        db.session.commit()
        current_app.logger.info(
            f"Subscription {subscription.id} cancelled for user {user.email}"
        )


def _handle_invoice_paid(invoice):
    """Handle successful invoice payment (for recurring subscriptions)"""
    current_app.logger.info(f"Invoice paid: {invoice.id}")


def _handle_invoice_failed(invoice):
    """Handle failed invoice payment"""
    current_app.logger.warning(f"Invoice payment failed: {invoice.id}")
