"""
Rotas para integração com Stripe
"""

import json
import os

import stripe
from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models import (
    CreditPackage,
    CreditTransaction,
    UserCredits,
)
from app.stripe_integration import bp

# Configurar Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


@bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    """Cria uma sessão de checkout do Stripe"""
    try:
        data = request.get_json()
        package_slug = data.get("package_slug")

        if not package_slug:
            return jsonify({"error": "Package slug é obrigatório"}), 400

        # Buscar pacote
        package = CreditPackage.query.filter_by(
            slug=package_slug, is_active=True
        ).first()

        if not package:
            return jsonify({"error": "Pacote não encontrado"}), 404

        # Verificar se o Stripe está configurado
        if not stripe.api_key or stripe.api_key == "sk_test_dummy":
            return jsonify(
                {"error": "Stripe não configurado. Configure STRIPE_SECRET_KEY no .env"}
            ), 500

        # Criar ou obter customer do Stripe
        if not current_user.stripe_customer_id:
            # Criar customer no Stripe
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                metadata={
                    "user_id": current_user.id,
                    "username": current_user.username,
                },
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()

        # URLs de sucesso e cancelamento
        success_url = url_for(
            "stripe_integration.checkout_success",
            session_id="{CHECKOUT_SESSION_ID}",
            _external=True,
        )
        cancel_url = url_for("ai.buy_credits", slug=package_slug, _external=True)

        # Criar sessão de checkout
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "brl",
                        "product_data": {
                            "name": package.name,
                            "description": f"{package.total_credits} créditos de IA"
                            + (
                                f" ({package.credits} + {package.bonus_credits} bônus)"
                                if package.bonus_credits > 0
                                else ""
                            ),
                            "images": [],
                        },
                        "unit_amount": int(float(package.price) * 100),  # Centavos
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": current_user.id,
                "package_id": package.id,
                "package_slug": package.slug,
                "credits": package.credits,
                "bonus_credits": package.bonus_credits or 0,
                "total_credits": package.total_credits,
            },
        )

        return jsonify({"checkout_url": checkout_session.url})

    except stripe.error.StripeError as e:
        current_app.logger.error(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Erro ao processar pagamento: {str(e)}"}), 500
    except Exception as e:
        current_app.logger.error(f"Error creating checkout: {str(e)}")
        return jsonify({"error": "Erro interno ao processar pagamento"}), 500


@bp.route("/checkout/success")
@login_required
def checkout_success():
    """Página de sucesso após checkout"""
    session_id = request.args.get("session_id")

    if not session_id:
        return redirect(url_for("ai.credits_dashboard"))

    try:
        # Recuperar sessão do Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == "paid":
            # Buscar pacote
            package_id = session.metadata.get("package_id")
            package = CreditPackage.query.get(package_id)

            if package:
                # Adicionar créditos ao usuário
                user_credits = UserCredits.get_or_create(current_user.id)

                # Créditos base
                user_credits.add_credits(package.credits, source="purchase")

                # Créditos bônus
                if package.bonus_credits > 0:
                    user_credits.add_credits(package.bonus_credits, source="bonus")

                # Registrar transação de compra
                transaction = CreditTransaction(
                    user_id=current_user.id,
                    transaction_type="purchase",
                    amount=package.credits,
                    balance_after=user_credits.balance,
                    description=f"Compra de {package.name}",
                    package_id=package.id,
                    payment_intent_id=session.payment_intent,
                    metadata=json.dumps(
                        {
                            "session_id": session_id,
                            "amount_paid": session.amount_total / 100,
                            "currency": session.currency,
                        }
                    ),
                )
                db.session.add(transaction)

                # Registrar bônus se houver
                if package.bonus_credits > 0:
                    bonus_transaction = CreditTransaction(
                        user_id=current_user.id,
                        transaction_type="bonus",
                        amount=package.bonus_credits,
                        balance_after=user_credits.balance,
                        description=f"Bônus de {package.name}",
                        package_id=package.id,
                        payment_intent_id=session.payment_intent,
                    )
                    db.session.add(bonus_transaction)

                db.session.commit()

                return render_template(
                    "stripe_integration/success.html",
                    package=package,
                    session=session,
                )

    except stripe.error.StripeError as e:
        current_app.logger.error(f"Error retrieving session: {str(e)}")

    return redirect(url_for("ai.credits_dashboard"))


@bp.route("/checkout/cancel")
@login_required
def checkout_cancel():
    """Página de cancelamento de checkout"""
    return render_template("stripe_integration/cancel.html")


@bp.route("/webhook", methods=["POST"])
def stripe_webhook():
    """Webhook do Stripe para eventos de pagamento"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        current_app.logger.warning(
            "STRIPE_WEBHOOK_SECRET não configurado, pulando verificação"
        )
        return jsonify({"status": "ignored"}), 200

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError as e:
        # Payload inválido
        current_app.logger.error(f"Invalid payload: {str(e)}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Assinatura inválida
        current_app.logger.error(f"Invalid signature: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400

    # Processar eventos
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        handle_checkout_completed(session)

    elif event["type"] == "checkout.session.expired":
        session = event["data"]["object"]
        current_app.logger.warning(
            f"Checkout session {session['id']} expirou sem pagamento"
        )

    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        current_app.logger.info(f"PaymentIntent {payment_intent['id']} succeeded")

    elif event["type"] == "payment_intent.canceled":
        payment_intent = event["data"]["object"]
        current_app.logger.warning(
            f"PaymentIntent {payment_intent['id']} foi cancelado"
        )

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        current_app.logger.error(f"PaymentIntent {payment_intent['id']} failed")

    return jsonify({"status": "success"}), 200


def handle_checkout_completed(session):
    """Processa checkout completado"""
    try:
        user_id = int(session["metadata"]["user_id"])
        package_id = int(session["metadata"]["package_id"])
        credits = int(session["metadata"]["credits"])
        bonus_credits = int(session["metadata"].get("bonus_credits", 0))

        # Verificar se já foi processado
        existing = CreditTransaction.query.filter_by(
            payment_intent_id=session.get("payment_intent")
        ).first()

        if existing:
            current_app.logger.info(
                f"Transaction already processed for session {session['id']}"
            )
            return

        # Adicionar créditos
        user_credits = UserCredits.get_or_create(user_id)
        user_credits.add_credits(credits, source="purchase")

        if bonus_credits > 0:
            user_credits.add_credits(bonus_credits, source="bonus")

        # Registrar transação
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type="purchase",
            amount=credits,
            balance_after=user_credits.balance,
            description="Compra via Stripe",
            package_id=package_id,
            payment_intent_id=session.get("payment_intent"),
            metadata=json.dumps(
                {
                    "session_id": session["id"],
                    "amount_paid": session["amount_total"] / 100,
                    "currency": session["currency"],
                }
            ),
        )
        db.session.add(transaction)

        if bonus_credits > 0:
            bonus_transaction = CreditTransaction(
                user_id=user_id,
                transaction_type="bonus",
                amount=bonus_credits,
                balance_after=user_credits.balance,
                description="Bônus via Stripe",
                package_id=package_id,
            )
            db.session.add(bonus_transaction)

        db.session.commit()

        current_app.logger.info(
            f"Credits added for user {user_id}: {credits} + {bonus_credits} bonus"
        )

    except Exception as e:
        current_app.logger.error(f"Error processing checkout: {str(e)}")
        db.session.rollback()
