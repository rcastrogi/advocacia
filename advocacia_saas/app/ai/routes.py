"""
Blueprint para funcionalidades de IA e sistema de créditos.
"""

import json
import os
from datetime import datetime, timezone

import mercadopago
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app import limiter
from app.ai.repository import (
    AIGenerationRepository,
    AISessionManager,
    CreditPackageRepository,
    CreditTransactionRepository,
    UserCreditsRepository,
)
from app.decorators import require_feature
from app.models import (
    CreditPackage,
    CreditTransaction,
    UserCredits,
)
from app.services.ai_service import CREDIT_COSTS, PREMIUM_OPERATIONS, ai_service
from app.services.document_service import (
    extract_document_text,
    get_supported_formats,
    validate_document_file,
)

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
    return CreditTransactionRepository.create(
        {
            "user_id": user_id,
            "transaction_type": transaction_type,
            "amount": amount,
            "description": description,
            "package_id": package_id,
            "generation_id": generation_id,
            "payment_intent_id": payment_intent_id,
        }
    )


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
    return AIGenerationRepository.create(
        {
            "user_id": user_id,
            "generation_type": generation_type,
            "petition_type_slug": petition_type_slug,
            "section_name": section_name,
            "credits_used": credits_used,
            "model_used": metadata.get("model", "gpt-4o-mini"),
            "tokens_input": metadata.get("tokens_input"),
            "tokens_output": metadata.get("tokens_output"),
            "tokens_total": metadata.get("tokens_total"),
            "response_time_ms": metadata.get("response_time_ms"),
            "input_data": input_data,
            "output_content": output_content,
            "status": status,
            "error_message": error_message,
        }
    )


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

    # Buscar chave pública do Mercado Pago para pagamentos únicos
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
    # Em produção, isso seria chamado pelo webhook do Mercado Pago
    data = request.get_json()

    amount = data.get("amount", 0)
    source = data.get("source", "bonus")
    description = data.get("description", "Créditos adicionados")

    if amount <= 0:
        return jsonify({"success": False, "error": "Quantidade inválida"}), 400

    user_credits = get_user_credits()
    user_credits.add_credits(amount, source)

    record_transaction(current_user.id, source, amount, description)

    AISessionManager.commit()

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
@require_feature("ai_petitions")
@limiter.limit("20 per hour")  # Limite para geração de seções
def api_generate_section():
    """Gera uma seção de petição usando IA"""
    if not ai_service.is_configured():
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Serviço de IA não configurado. Entre em contato com o suporte.",
                }
            ),
            503,
        )

    data = request.get_json()

    section_type = data.get("section_type", "fatos")
    petition_type = data.get("petition_type", "")
    context = data.get("context", {})
    existing_content = data.get("existing_content", "")
    premium = data.get("premium", False)

    # Seções de fundamentação são complexas - usam mais créditos e GPT-4o
    fundamentos_sections = {
        "direito",
        "fundamentos",
        "fundamentacao",
        "fundamentacao-juridica",
        "fundamentos-juridicos",
        "do-direito",
        "dos-fundamentos",
    }
    is_fundamentos = section_type.lower().replace("_", "-") in fundamentos_sections

    # Determina o custo - fundamentação é mais cara
    generation_type = "fundamentos" if is_fundamentos else "section"
    credit_cost = ai_service.get_credit_cost(generation_type)

    # Fundamentação sempre usa premium (GPT-4o)
    if is_fundamentos:
        premium = True

    # Verifica créditos (master não precisa)
    if not has_sufficient_credits(credit_cost):
        user_credits = get_user_credits()
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Créditos insuficientes",
                    "credits_required": credit_cost,
                    "credits_available": user_credits.balance,
                }
            ),
            402,
        )

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

        AISessionManager.commit()

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
        AISessionManager.rollback()

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
        AISessionManager.commit()

        return jsonify(
            {"success": False, "error": f"Erro ao gerar conteúdo: {str(e)}"}
        ), 500


@ai_bp.route("/api/generate/full-petition", methods=["POST"])
@login_required
@require_feature("ai_petitions")
@limiter.limit("10 per hour")  # Limite menor para petições completas (mais custosas)
def api_generate_full_petition():
    """Gera uma petição completa usando IA"""
    if not ai_service.is_configured():
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Serviço de IA não configurado. Entre em contato com o suporte.",
                }
            ),
            503,
        )

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
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Créditos insuficientes",
                    "credits_required": credit_cost,
                    "credits_available": user_credits.balance,
                }
            ),
            402,
        )

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

        AISessionManager.commit()

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
        AISessionManager.rollback()

        record_ai_generation(
            user_id=current_user.id,
            generation_type=generation_type,
            credits_used=0,
            metadata={},
            petition_type_slug=petition_type,
            status="failed",
            error_message=str(e),
        )
        AISessionManager.commit()

        return jsonify(
            {"success": False, "error": f"Erro ao gerar petição: {str(e)}"}
        ), 500


@ai_bp.route("/api/generate/improve", methods=["POST"])
@login_required
@require_feature("ai_petitions")
@limiter.limit("15 per hour")  # Limite para melhoria de texto
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
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Créditos insuficientes",
                    "credits_required": credit_cost,
                    "credits_available": user_credits.balance,
                }
            ),
            402,
        )

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

        AISessionManager.commit()

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
        AISessionManager.rollback()
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
    generation = AIGenerationRepository.get_by_id(generation_id, current_user.id)
    if not generation:
        return jsonify({"success": False, "error": "Geração não encontrada"}), 404

    data = request.get_json()

    AIGenerationRepository.update_feedback(
        generation,
        rating=data.get("rating"),
        was_used=data.get("was_used"),
    )

    return jsonify({"success": True})


# =============================================================================
# ANÁLISE DE DOCUMENTOS COM IA
# =============================================================================


@ai_bp.route("/analyze-document")
@login_required
def analyze_document_page():
    """Página de análise de documentos"""
    user_credits = get_user_credits()
    credit_cost = CREDIT_COSTS.get("analyze_document", 4)

    return render_template(
        "ai/analyze_document.html",
        credits=user_credits,
        credit_cost=credit_cost,
        supported_formats=get_supported_formats(),
    )


@ai_bp.route("/api/analyze-document", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def api_analyze_document():
    """API para análise de documento com IA"""
    credit_cost = CREDIT_COSTS.get("analyze_document", 4)

    # Verificar créditos
    if not has_sufficient_credits(credit_cost):
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
            }
        ), 402

    # Verificar arquivo
    if "document" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    file = request.files["document"]
    is_valid, error_msg = validate_document_file(file)

    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    try:
        # Extrair texto do documento
        document_text, doc_metadata = extract_document_text(file)

        if not document_text or len(document_text.strip()) < 50:
            return jsonify(
                {
                    "success": False,
                    "error": "Não foi possível extrair texto suficiente do documento",
                }
            ), 400

        # Analisar com IA
        analysis, ai_metadata = ai_service.analyze_document(
            document_text, file.filename
        )

        # Descontar créditos
        if not is_master_user():
            use_credits_if_needed(credit_cost)

        # Salvar na sessão para uso posterior
        session["last_document_text"] = document_text[:20000]
        session["last_document_analysis"] = analysis
        session["last_document_name"] = file.filename

        # Registrar geração via repository
        AIGenerationRepository.create(
            {
                "user_id": current_user.id,
                "generation_type": "analyze_document",
                "prompt": f"Análise de: {file.filename}",
                "result": analysis[:5000],
                "tokens_used": ai_metadata.get("tokens_total", 0),
                "model_used": ai_metadata.get("model", "gpt-4o"),
                "credits_used": credit_cost,
            }
        )
        AISessionManager.commit()

        return jsonify(
            {
                "success": True,
                "analysis": analysis,
                "document_info": doc_metadata,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao analisar documento: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": f"Erro ao processar documento: {str(e)}",
            }
        ), 500


@ai_bp.route("/api/generate-fundamentos", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def api_generate_fundamentos():
    """API para gerar fundamentação jurídica baseada em documento"""
    credit_cost = CREDIT_COSTS.get("fundamentos", 3)

    # Verificar créditos
    if not has_sufficient_credits(credit_cost):
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
            }
        ), 402

    data = request.get_json() or {}

    # Pegar documento da sessão ou do request
    document_text = data.get("document_text") or session.get("last_document_text")
    document_analysis = data.get("document_analysis") or session.get(
        "last_document_analysis"
    )
    petition_type = data.get("petition_type")
    additional_context = data.get("additional_context")

    if not document_text and not document_analysis:
        return jsonify(
            {
                "success": False,
                "error": "Nenhum documento carregado. Faça upload e análise primeiro.",
            }
        ), 400

    try:
        # Gerar fundamentação
        fundamentos, ai_metadata = ai_service.generate_fundamentos_from_document(
            document_text=document_text,
            document_analysis=document_analysis,
            petition_type=petition_type,
            additional_context=additional_context,
        )

        # Descontar créditos
        if not is_master_user():
            use_credits_if_needed(credit_cost)

        # Registrar geração via repository
        AIGenerationRepository.create(
            {
                "user_id": current_user.id,
                "generation_type": "fundamentos",
                "prompt": "Fundamentação baseada em documento",
                "result": fundamentos[:5000],
                "tokens_used": ai_metadata.get("tokens_total", 0),
                "model_used": ai_metadata.get("model", "gpt-4o"),
                "credits_used": credit_cost,
            }
        )
        AISessionManager.commit()

        return jsonify(
            {
                "success": True,
                "fundamentos": fundamentos,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar fundamentação: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": f"Erro ao gerar fundamentação: {str(e)}",
            }
        ), 500


@ai_bp.route("/api/analyze-risk", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def api_analyze_risk():
    """API para analisar riscos e chances de êxito de uma petição"""
    from app.services.ai_service import get_credit_cost

    credit_cost = get_credit_cost("analyze_risk")

    # Verificar créditos
    if not has_sufficient_credits(credit_cost):
        return jsonify(
            {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_needed": credit_cost,
            }
        ), 402

    # Verificar configuração da API
    if not ai_service.is_configured():
        return jsonify(
            {
                "success": False,
                "error": "API de IA não configurada",
            }
        ), 503

    data = request.get_json()
    if not data:
        return jsonify(
            {
                "success": False,
                "error": "Dados não fornecidos",
            }
        ), 400

    # Extrair dados
    petition_content = data.get("petition_content", "")
    petition_type = data.get("petition_type", "")
    fatos = data.get("fatos", "")
    pedidos = data.get("pedidos", "")
    fundamentacao = data.get("fundamentacao", "")

    # Validar que há conteúdo para analisar
    if not petition_content and not (fatos or pedidos or fundamentacao):
        return jsonify(
            {
                "success": False,
                "error": "Forneça o conteúdo da petição ou as seções individuais",
            }
        ), 400

    try:
        # Gerar análise
        analysis_json, ai_metadata = ai_service.analyze_risk(
            petition_content=petition_content,
            petition_type=petition_type,
            fatos=fatos,
            pedidos=pedidos,
            fundamentacao=fundamentacao,
        )

        # Debitar créditos
        if not use_credits_if_needed(credit_cost):
            return jsonify(
                {
                    "success": False,
                    "error": "Erro ao debitar créditos",
                }
            ), 500

        # Tentar parsear o JSON da resposta
        import json

        try:
            # Limpar possíveis caracteres extras
            analysis_json = analysis_json.strip()
            if analysis_json.startswith("```json"):
                analysis_json = analysis_json[7:]
            if analysis_json.startswith("```"):
                analysis_json = analysis_json[3:]
            if analysis_json.endswith("```"):
                analysis_json = analysis_json[:-3]
            analysis_json = analysis_json.strip()

            analysis = json.loads(analysis_json)
        except json.JSONDecodeError:
            # Se não conseguir parsear, retornar como texto
            analysis = {"raw_analysis": analysis_json, "parse_error": True}

        # Registrar transação
        record_transaction(
            user_id=current_user.id,
            transaction_type="usage",
            amount=-credit_cost,
            description=f"Análise de riscos: {petition_type or 'Petição'}",
        )

        # Registrar geração
        generation = record_ai_generation(
            user_id=current_user.id,
            generation_type="analyze_risk",
            credits_used=credit_cost,
            input_data={"petition_type": petition_type},
            output_text=str(analysis)[:5000],
            model_used=ai_metadata.get("model", "gpt-4o"),
        )

        return jsonify(
            {
                "success": True,
                "analysis": analysis,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao analisar riscos: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": f"Erro ao analisar petição: {str(e)}",
            }
        ), 500


# =============================================================================
# CHECKOUT MERCADO PAGO - CRÉDITOS IA
# =============================================================================


@ai_bp.route("/credits/checkout/<slug>", methods=["POST"])
@login_required
def credits_checkout(slug):
    """Cria preferência de pagamento no Mercado Pago para créditos (pagamentos únicos)"""
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


# =============================================================================
# PIX PARA CRÉDITOS DE IA
# =============================================================================


@ai_bp.route("/credits/pix/<slug>")
@login_required
def credits_pix_page(slug):
    """Página de pagamento PIX para créditos de IA"""
    package = CreditPackage.query.filter_by(slug=slug, is_active=True).first_or_404()
    return render_template("ai/credits_pix.html", package=package)


@ai_bp.route("/credits/create-pix/<slug>", methods=["POST"])
@login_required
def create_credits_pix(slug):
    """Cria pagamento PIX para créditos de IA"""
    package = CreditPackage.query.filter_by(slug=slug, is_active=True).first_or_404()

    mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not mp_access_token:
        return jsonify({"error": "Mercado Pago não configurado"}), 500

    mp_sdk = mercadopago.SDK(mp_access_token)

    # Criar pagamento PIX
    payment_data = {
        "transaction_amount": float(package.price),
        "description": f"{package.name} - {package.total_credits} créditos de IA",
        "payment_method_id": "pix",
        "payer": {
            "email": current_user.email,
            "first_name": current_user.full_name.split()[0]
            if current_user.full_name
            else current_user.username,
            "last_name": current_user.full_name.split()[-1]
            if current_user.full_name and len(current_user.full_name.split()) > 1
            else "",
        },
        "metadata": {
            "user_id": current_user.id,
            "package_id": package.id,
            "credits": package.credits,
            "bonus_credits": package.bonus_credits or 0,
            "type": "credit_purchase",
        },
        "external_reference": f"credits_pix_{current_user.id}_{package.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
    }

    try:
        payment_response = mp_sdk.payment().create(payment_data)
        payment = payment_response["response"]

        if payment.get("status") == "pending":
            pix_data = payment.get("point_of_interaction", {}).get(
                "transaction_data", {}
            )

            return jsonify(
                {
                    "success": True,
                    "payment_id": payment["id"],
                    "qr_code": pix_data.get("qr_code"),
                    "qr_code_base64": pix_data.get("qr_code_base64"),
                    "expiration": payment.get("date_of_expiration"),
                }
            )
        else:
            return jsonify(
                {
                    "error": f"Erro ao criar PIX: {payment.get('status_detail', 'unknown')}"
                }
            ), 400

    except Exception as e:
        current_app.logger.error(f"Erro ao criar PIX de créditos: {str(e)}")
        return jsonify({"error": "Erro ao processar pagamento PIX"}), 500


@ai_bp.route("/credits/check-pix/<int:payment_id>")
@login_required
def check_credits_pix(payment_id):
    """Verifica status do pagamento PIX de créditos"""
    mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not mp_access_token:
        return jsonify({"error": "Mercado Pago não configurado"}), 500

    mp_sdk = mercadopago.SDK(mp_access_token)

    try:
        payment_response = mp_sdk.payment().get(payment_id)
        payment = payment_response["response"]

        status = payment.get("status")

        # Se aprovado, processar créditos
        if status == "approved":
            metadata = payment.get("metadata", {})
            user_id = metadata.get("user_id")
            package_id = metadata.get("package_id")

            if user_id == current_user.id and package_id:
                # Verificar se já foi processado
                existing = CreditTransaction.query.filter_by(
                    payment_intent_id=str(payment_id)
                ).first()

                if not existing:
                    _process_credit_purchase(payment_id, user_id, package_id, metadata)

        return jsonify(
            {
                "success": True,
                "status": status,
                "status_detail": payment.get("status_detail"),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao verificar PIX: {str(e)}")
        return jsonify({"error": "Erro ao verificar pagamento"}), 500


def _process_credit_purchase(payment_id, user_id, package_id, metadata):
    """Processa compra de créditos após pagamento aprovado"""
    try:
        package = CreditPackageRepository.get_by_id(package_id)
        if not package:
            return False

        user_credits = UserCreditsRepository.get_or_create(user_id)

        # Adicionar créditos
        credits_to_add = metadata.get("credits", package.credits)
        bonus_to_add = metadata.get("bonus_credits", package.bonus_credits or 0)

        user_credits.add_credits(credits_to_add, source="purchase")
        if bonus_to_add > 0:
            user_credits.add_credits(bonus_to_add, source="bonus")

        # Registrar transação principal via repository
        CreditTransactionRepository.create(
            {
                "user_id": user_id,
                "transaction_type": "purchase",
                "amount": credits_to_add,
                "description": f"Compra PIX - {package.name}",
                "package_id": package_id,
                "payment_intent_id": str(payment_id),
                "metadata": {"payment_method": "pix", "bonus": bonus_to_add},
            }
        )

        # Registrar bônus separadamente
        if bonus_to_add > 0:
            CreditTransactionRepository.create(
                {
                    "user_id": user_id,
                    "transaction_type": "bonus",
                    "amount": bonus_to_add,
                    "description": f"Bônus - {package.name}",
                    "package_id": package_id,
                }
            )

        AISessionManager.commit()

        current_app.logger.info(
            f"✅ Créditos PIX processados: user={user_id}, "
            f"credits={credits_to_add}, bonus={bonus_to_add}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Erro ao processar compra de créditos: {str(e)}")
        AISessionManager.rollback()
        return False


@ai_bp.route("/credits/success")
@login_required
def credits_success():
    """Página de sucesso após pagamento de créditos"""
    package_id = request.args.get("package_id", type=int)
    payment_id = request.args.get("payment_id")

    if not package_id:
        return redirect(url_for("ai.credits_dashboard"))

    package = CreditPackageRepository.get_by_id(package_id)

    if payment_id:
        # Adicionar créditos
        user_credits = UserCreditsRepository.get_or_create(current_user.id)
        user_credits.add_credits(package.credits, source="purchase")

        if package.bonus_credits:
            user_credits.add_credits(package.bonus_credits, source="bonus")

        # Registrar transação via repository
        CreditTransactionRepository.create(
            {
                "user_id": current_user.id,
                "transaction_type": "purchase",
                "amount": package.credits,
                "description": f"Compra de {package.name}",
                "package_id": package.id,
                "payment_intent_id": payment_id,
                "metadata": {"payment_id": payment_id, "gateway": "mercadopago"},
            }
        )

        if package.bonus_credits:
            CreditTransactionRepository.create(
                {
                    "user_id": current_user.id,
                    "transaction_type": "bonus",
                    "amount": package.bonus_credits,
                    "description": f"Bônus de {package.name}",
                    "package_id": package.id,
                }
            )

        AISessionManager.commit()

    return render_template(
        "ai/credits_success.html", package=package, payment_id=payment_id
    )


@ai_bp.route("/credits/failure")
@login_required
def credits_failure():
    """Página de falha no pagamento"""
    return render_template("ai/credits_failure.html")


@ai_bp.route("/webhook/mercadopago/credits", methods=["POST"])
def mercadopago_webhook_credits():
    """Webhook do Mercado Pago para pagamentos de créditos (checkout e PIX)"""
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

                # Verificar se é compra de créditos (checkout ou PIX)
                payment_type = metadata.get("type", "")
                is_credit_purchase = payment_type == "credit_purchase" or (
                    user_id
                    and package_id
                    and "credits" in str(payment.get("external_reference", ""))
                )

                if user_id and package_id and is_credit_purchase:
                    # Verificar duplicata
                    existing = CreditTransaction.query.filter_by(
                        payment_intent_id=str(payment_id)
                    ).first()

                    if not existing:
                        _process_credit_purchase(
                            payment_id, user_id, package_id, metadata
                        )
                        current_app.logger.info(
                            f"✅ Webhook: Créditos processados payment_id={payment_id}"
                        )

        except Exception as e:
            current_app.logger.error(f"Erro no webhook MP créditos: {str(e)}")

    return jsonify({"status": "ok"}), 200
