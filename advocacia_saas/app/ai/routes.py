"""
Blueprint para funcionalidades de IA e sistema de créditos.
"""

import json
import os
from datetime import datetime

import mercadopago
from flask import (
    Blueprint,
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
    AIGeneration,
    CreditPackage,
    CreditTransaction,
    UserCredits,
)
from app.services.ai_service import CREDIT_COSTS, ai_service

ai_bp = Blueprint("ai", __name__, url_prefix="/ai")


# =============================================================================
# HELPERS
# =============================================================================


def is_master_user():
    """Verifica se o usuário atual é master (admin)"""
    return current_user.user_type == "master"


def get_user_credits():
    """Obtém ou cria o registro de créditos do usuário atual"""
    return UserCredits.get_or_create(current_user.id)


def has_sufficient_credits(amount):
    """Verifica se o usuário tem créditos suficientes (master sempre tem)"""
    if is_master_user():
        return True
    user_credits = get_user_credits()
    return user_credits.has_credits(amount)


def use_credits_if_needed(amount):
    """Debita créditos se necessário (master não paga)"""
    if is_master_user():
        return True  # Master não gasta créditos
    user_credits = get_user_credits()
    return user_credits.use_credits(amount)


def record_transaction(
    user_id,
    transaction_type,
    amount,
    description,
    package_id=None,
    generation_id=None,
    payment_intent_id=None,
):
    """Registra uma transação de créditos"""
    user_credits = UserCredits.get_or_create(user_id)

    transaction = CreditTransaction(
        user_id=user_id,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=user_credits.balance,
        description=description,
        package_id=package_id,
        generation_id=generation_id,
        payment_intent_id=payment_intent_id,
    )
    db.session.add(transaction)
    return transaction


def record_ai_generation(
    user_id,
    generation_type,
    credits_used,
    metadata,
    petition_type_slug=None,
    section_name=None,
    input_data=None,
    output_content=None,
    status="completed",
    error_message=None,
):
    """Registra uma geração de IA"""
    generation = AIGeneration(
        user_id=user_id,
        generation_type=generation_type,
        petition_type_slug=petition_type_slug,
        section_name=section_name,
        credits_used=credits_used,
        model_used=metadata.get("model", "gpt-4o-mini"),
        tokens_input=metadata.get("tokens_input"),
        tokens_output=metadata.get("tokens_output"),
        tokens_total=metadata.get("tokens_total"),
        response_time_ms=metadata.get("response_time_ms"),
        input_data=json.dumps(input_data) if input_data else None,
        output_content=output_content,
        status=status,
        error_message=error_message,
        completed_at=datetime.utcnow() if status == "completed" else None,
    )
    generation.calculate_cost()
    db.session.add(generation)
    return generation


# =============================================================================
# ROTAS DE CRÉDITOS
# =============================================================================


@ai_bp.route("/credits")
@login_required
def credits_dashboard():
    """Dashboard de créditos do usuário"""
    user_credits = get_user_credits()
    packages = (
        CreditPackage.query.filter_by(is_active=True)
        .order_by(CreditPackage.sort_order)
        .all()
    )

    # Últimas transações
    transactions = (
        CreditTransaction.query.filter_by(user_id=current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    # Estatísticas de uso
    total_generations = AIGeneration.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "ai/credits_dashboard.html",
        credits=user_credits,
        packages=packages,
        transactions=transactions,
        total_generations=total_generations,
        credit_costs=CREDIT_COSTS,
    )


@ai_bp.route("/credits/buy/<slug>")
@login_required
def buy_credits(slug):
    """Página de compra de pacote específico"""
    package = CreditPackage.query.filter_by(slug=slug, is_active=True).first_or_404()

    # Buscar chave pública do Mercado Pago
    mp_public_key = current_app.config.get("MERCADOPAGO_PUBLIC_KEY")

    return render_template(
        "ai/buy_credits.html", package=package, mp_public_key=mp_public_key
    )


@ai_bp.route("/credits/history")
@login_required
def credits_history():
    """Histórico completo de transações"""
    page = request.args.get("page", 1, type=int)
    transactions = (
        CreditTransaction.query.filter_by(user_id=current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .paginate(page=page, per_page=50)
    )

    return render_template("ai/credits_history.html", transactions=transactions)


@ai_bp.route("/generations")
@login_required
def generations_history():
    """Histórico de gerações de IA"""
    page = request.args.get("page", 1, type=int)
    generations = (
        AIGeneration.query.filter_by(user_id=current_user.id)
        .order_by(AIGeneration.created_at.desc())
        .paginate(page=page, per_page=20)
    )

    return render_template("ai/generations_history.html", generations=generations)


# =============================================================================
# API DE CRÉDITOS
# =============================================================================


@ai_bp.route("/api/credits/balance")
@login_required
def api_credits_balance():
    """Retorna o saldo de créditos do usuário"""
    if is_master_user():
        return jsonify(
            {
                "success": True,
                "balance": "∞",
                "is_unlimited": True,
                "total_purchased": 0,
                "total_used": 0,
            }
        )

    user_credits = get_user_credits()
    return jsonify(
        {
            "success": True,
            "balance": user_credits.balance,
            "is_unlimited": False,
            "total_purchased": user_credits.total_purchased,
            "total_used": user_credits.total_used,
        }
    )


@ai_bp.route("/api/credits/add", methods=["POST"])
@login_required
def api_add_credits():
    """Adiciona créditos (para uso interno/admin ou após pagamento)"""
    # Em produção, isso seria chamado pelo webhook do Stripe
    data = request.get_json()

    amount = data.get("amount", 0)
    source = data.get("source", "bonus")
    description = data.get("description", "Créditos adicionados")

    if amount <= 0:
        return jsonify({"success": False, "error": "Quantidade inválida"}), 400

    user_credits = get_user_credits()
    user_credits.add_credits(amount, source)

    record_transaction(current_user.id, source, amount, description)

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "new_balance": user_credits.balance,
            "message": f"{amount} créditos adicionados!",
        }
    )


# =============================================================================
# API DE GERAÇÃO DE IA
# =============================================================================


@ai_bp.route("/api/generate/section", methods=["POST"])
@login_required
def api_generate_section():
    """Gera uma seção de petição usando IA"""
    if not ai_service.is_configured():
        return jsonify(
            {
                "success": False,
                "error": "Serviço de IA não configurado. Entre em contato com o suporte.",
            }
        ), 503

    data = request.get_json()

    section_type = data.get("section_type", "fatos")
    petition_type = data.get("petition_type", "")
    context = data.get("context", {})
    existing_content = data.get("existing_content", "")
    premium = data.get("premium", False)

    # Determina o custo
    generation_type = "section"
    credit_cost = ai_service.get_credit_cost(generation_type)

    # Verifica créditos (master não precisa)
    if not has_sufficient_credits(credit_cost):
        user_credits = get_user_credits()
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }
        ), 402

    try:
        # Adiciona tipo de petição ao contexto
        context["petition_type"] = petition_type

        # Gera o conteúdo
        content, metadata = ai_service.generate_section(
            section_type=section_type,
            context=context,
            existing_content=existing_content,
            premium=premium,
        )

        # Debita créditos (master não paga)
        actual_cost = 0 if is_master_user() else credit_cost
        if not is_master_user():
            use_credits_if_needed(credit_cost)

        user_credits = get_user_credits()

        # Registra a geração
        generation = record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=actual_cost,
            metadata=metadata,
            petition_type_slug=petition_type,
            section_name=section_type,
            input_data=context,
            output_content=content,
        )

        # Registra transação apenas se gastou créditos
        if actual_cost > 0:
            record_transaction(
                current_user.id,
                "usage",
                -actual_cost,
                f"Geração de seção: {section_type}",
                generation_id=generation.id,
            )

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance
                if not is_master_user()
                else "∞",
                "metadata": {
                    "model": metadata.get("model"),
                    "tokens_used": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                },
            }
        )

    except Exception as e:
        db.session.rollback()

        # Registra falha
        record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=0,
            metadata={},
            petition_type_slug=petition_type,
            section_name=section_type,
            status="failed",
            error_message=str(e),
        )
        db.session.commit()

        return jsonify(
            {"success": False, "error": f"Erro ao gerar conteúdo: {str(e)}"}
        ), 500


@ai_bp.route("/api/generate/full-petition", methods=["POST"])
@login_required
def api_generate_full_petition():
    """Gera uma petição completa usando IA"""
    if not ai_service.is_configured():
        return jsonify(
            {
                "success": False,
                "error": "Serviço de IA não configurado. Entre em contato com o suporte.",
            }
        ), 503

    data = request.get_json()

    petition_type = data.get("petition_type", "")
    context = data.get("context", {})
    premium = data.get("premium", True)  # Petição completa usa premium por padrão

    # Determina o custo
    generation_type = "full_petition"
    credit_cost = ai_service.get_credit_cost(generation_type)

    # Verifica créditos (master não precisa)
    if not has_sufficient_credits(credit_cost):
        user_credits = get_user_credits()
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }
        ), 402

    try:
        # Gera a petição
        content, metadata = ai_service.generate_full_petition(
            petition_type=petition_type, context=context, premium=premium
        )

        # Debita créditos (master não paga)
        actual_cost = 0 if is_master_user() else credit_cost
        if not is_master_user():
            use_credits_if_needed(credit_cost)

        user_credits = get_user_credits()

        # Registra a geração
        generation = record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=actual_cost,
            metadata=metadata,
            petition_type_slug=petition_type,
            input_data=context,
            output_content=content,
        )

        # Registra transação apenas se gastou créditos
        if actual_cost > 0:
            record_transaction(
                current_user.id,
                "usage",
                -actual_cost,
                f"Geração de petição completa: {petition_type}",
                generation_id=generation.id,
            )

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance
                if not is_master_user()
                else "∞",
                "metadata": {
                    "model": metadata.get("model"),
                    "tokens_used": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                },
            }
        )

    except Exception as e:
        db.session.rollback()

        record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=0,
            metadata={},
            petition_type_slug=petition_type,
            status="failed",
            error_message=str(e),
        )
        db.session.commit()

        return jsonify(
            {"success": False, "error": f"Erro ao gerar petição: {str(e)}"}
        ), 500


@ai_bp.route("/api/generate/improve", methods=["POST"])
@login_required
def api_improve_text():
    """Melhora um texto existente usando IA"""
    if not ai_service.is_configured():
        return jsonify(
            {"success": False, "error": "Serviço de IA não configurado."}
        ), 503

    data = request.get_json()

    text = data.get("text", "")
    context = data.get("context", "")
    premium = data.get("premium", False)

    if not text or len(text.strip()) < 10:
        return jsonify(
            {"success": False, "error": "Texto muito curto para melhorar"}
        ), 400

    # Determina o custo
    generation_type = "improve"
    credit_cost = ai_service.get_credit_cost(generation_type)

    # Verifica créditos (master não precisa)
    if not has_sufficient_credits(credit_cost):
        user_credits = get_user_credits()
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }
        ), 402

    try:
        content, metadata = ai_service.improve_text(
            text=text, context=context, premium=premium
        )

        # Debita créditos (master não paga)
        actual_cost = 0 if is_master_user() else credit_cost
        if not is_master_user():
            use_credits_if_needed(credit_cost)

        user_credits = get_user_credits()

        generation = record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=actual_cost,
            metadata=metadata,
            input_data={"text": text[:500], "context": context},
            output_content=content,
        )

        if actual_cost > 0:
            record_transaction(
                current_user.id,
                "usage",
                -actual_cost,
                "Melhoria de texto",
                generation_id=generation.id,
            )

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance
                if not is_master_user()
                else "∞",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"success": False, "error": f"Erro ao melhorar texto: {str(e)}"}
        ), 500


@ai_bp.route("/api/credit-costs")
@login_required
def api_credit_costs():
    """Retorna a tabela de custos de créditos"""
    return jsonify({"success": True, "costs": CREDIT_COSTS})


# =============================================================================
# FEEDBACK
# =============================================================================


@ai_bp.route("/api/generation/<int:generation_id>/feedback", methods=["POST"])
@login_required
def api_generation_feedback(generation_id):
    """Registra feedback sobre uma geração"""
    generation = AIGeneration.query.filter_by(
        id=generation_id, user_id=current_user.id
    ).first_or_404()

    data = request.get_json()

    if "rating" in data:
        generation.user_rating = min(5, max(1, int(data["rating"])))

    if "was_used" in data:
        generation.was_used = bool(data["was_used"])

    db.session.commit()

    return jsonify({"success": True})


# =============================================================================
# CHECKOUT MERCADO PAGO - CRÉDITOS IA
# =============================================================================


@ai_bp.route("/credits/checkout/<slug>", methods=["POST"])
@login_required
def credits_checkout(slug):
    """Cria preferência de pagamento no Mercado Pago para créditos"""
    package = CreditPackage.query.filter_by(slug=slug, is_active=True).first_or_404()

    mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not mp_access_token:
        return jsonify({"error": "Mercado Pago não configurado"}), 500

    mp_sdk = mercadopago.SDK(mp_access_token)

    # URLs de retorno
    success_url = request.host_url.rstrip("/") + url_for(
        "ai.credits_success", package_id=package.id
    )
    failure_url = request.host_url.rstrip("/") + url_for("ai.credits_failure")
    pending_url = request.host_url.rstrip("/") + url_for("ai.credits_pending")

    # Criar preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": package.name,
                "description": f"{package.total_credits} créditos de IA para geração de petições",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(package.price),
            }
        ],
        "payer": {
            "name": current_user.full_name or current_user.username,
            "email": current_user.email,
        },
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url,
        },
        "auto_return": "approved",
        "external_reference": f"credits_{current_user.id}_{package.id}",
        "metadata": {
            "user_id": current_user.id,
            "package_id": package.id,
            "credits": package.credits,
            "bonus_credits": package.bonus_credits or 0,
        },
    }

    try:
        preference_response = mp_sdk.preference().create(preference_data)
        preference = preference_response["response"]

        return jsonify(
            {
                "success": True,
                "init_point": preference["init_point"],
                "preference_id": preference["id"],
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao criar preferência MP: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento"}), 500


@ai_bp.route("/credits/success")
@login_required
def credits_success():
    """Página de sucesso após pagamento de créditos"""
    package_id = request.args.get("package_id", type=int)
    payment_id = request.args.get("payment_id")

    if not package_id:
        return redirect(url_for("ai.credits_dashboard"))

    package = CreditPackage.query.get(package_id)

    if payment_id:
        # Adicionar créditos
        user_credits = UserCredits.get_or_create(current_user.id)
        user_credits.add_credits(package.credits, source="purchase")

        if package.bonus_credits:
            user_credits.add_credits(package.bonus_credits, source="bonus")

        # Registrar transação
        transaction = CreditTransaction(
            user_id=current_user.id,
            transaction_type="purchase",
            amount=package.credits,
            balance_after=user_credits.balance,
            description=f"Compra de {package.name}",
            package_id=package.id,
            payment_intent_id=payment_id,
            metadata=json.dumps({"payment_id": payment_id, "gateway": "mercadopago"}),
        )
        db.session.add(transaction)

        if package.bonus_credits:
            bonus_transaction = CreditTransaction(
                user_id=current_user.id,
                transaction_type="bonus",
                amount=package.bonus_credits,
                balance_after=user_credits.balance,
                description=f"Bônus de {package.name}",
                package_id=package.id,
            )
            db.session.add(bonus_transaction)

        db.session.commit()

    return render_template(
        "ai/credits_success.html", package=package, payment_id=payment_id
    )


@ai_bp.route("/credits/failure")
@login_required
def credits_failure():
    """Página de falha no pagamento"""
    return render_template("ai/credits_failure.html")


@ai_bp.route("/credits/pending")
@login_required
def credits_pending():
    """Página de pagamento pendente"""
    return render_template("ai/credits_pending.html")


@ai_bp.route("/webhook/mercadopago/credits", methods=["POST"])
def mercadopago_webhook_credits():
    """Webhook do Mercado Pago para pagamentos de créditos"""
    data = request.get_json()

    if data.get("type") == "payment":
        payment_id = data["data"]["id"]

        mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        mp_sdk = mercadopago.SDK(mp_access_token)

        try:
            payment_info = mp_sdk.payment().get(payment_id)
            payment = payment_info["response"]

            if payment["status"] == "approved":
                # Extrair metadados
                metadata = payment.get("metadata", {})
                user_id = metadata.get("user_id")
                package_id = metadata.get("package_id")

                if user_id and package_id:
                    # Verificar duplicata
                    existing = CreditTransaction.query.filter_by(
                        payment_intent_id=str(payment_id)
                    ).first()

                    if not existing:
                        package = CreditPackage.query.get(package_id)
                        user_credits = UserCredits.get_or_create(user_id)

                        # Adicionar créditos
                        user_credits.add_credits(package.credits, source="purchase")
                        if package.bonus_credits:
                            user_credits.add_credits(
                                package.bonus_credits, source="bonus"
                            )

                        # Registrar transação
                        transaction = CreditTransaction(
                            user_id=user_id,
                            transaction_type="purchase",
                            amount=package.credits,
                            balance_after=user_credits.balance,
                            description="Compra via Mercado Pago",
                            package_id=package_id,
                            payment_intent_id=str(payment_id),
                        )
                        db.session.add(transaction)
                        db.session.commit()

                        current_app.logger.info(
                            f"Créditos adicionados via MP: {package.credits}"
                        )

        except Exception as e:
            current_app.logger.error(f"Erro no webhook MP: {str(e)}")

    return jsonify({"status": "ok"}), 200
