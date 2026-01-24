"""
AI Services - Camada de lógica de negócios para IA e créditos
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import mercadopago
from flask import current_app, session, url_for

from app import db
from app.ai.repository import (
    AIGenerationRepository,
    CreditPackageRepository,
    CreditTransactionRepository,
    UserCreditsRepository,
)
from app.services.ai_service import CREDIT_COSTS, ai_service
from app.services.document_service import extract_document_text, validate_document_file


class CreditsService:
    """Serviço para gerenciamento de créditos"""

    @staticmethod
    def is_master_user(user) -> bool:
        """Verifica se o usuário é master (admin)"""
        return user.user_type == "master"

    @staticmethod
    def get_user_credits(user_id: int):
        """Obtém ou cria o registro de créditos do usuário"""
        return UserCreditsRepository.get_or_create(user_id)

    @staticmethod
    def has_sufficient_credits(user, amount: int) -> bool:
        """Verifica se o usuário tem créditos suficientes (master sempre tem)"""
        if CreditsService.is_master_user(user):
            return True
        return UserCreditsRepository.has_credits(user.id, amount)

    @staticmethod
    def use_credits_if_needed(user, amount: int) -> bool:
        """Debita créditos se necessário (master não paga)"""
        if CreditsService.is_master_user(user):
            return True
        return UserCreditsRepository.use_credits(user.id, amount)

    @staticmethod
    def get_balance_info(user) -> dict[str, Any]:
        """Retorna informações de saldo do usuário"""
        if CreditsService.is_master_user(user):
            return {
                "success": True,
                "balance": "∞",
                "is_unlimited": True,
                "total_purchased": 0,
                "total_used": 0,
            }

        user_credits = CreditsService.get_user_credits(user.id)
        return {
            "success": True,
            "balance": user_credits.balance,
            "is_unlimited": False,
            "total_purchased": user_credits.total_purchased,
            "total_used": user_credits.total_used,
        }

    @staticmethod
    def add_credits(
        user_id: int, amount: int, source: str, description: str
    ) -> tuple[dict, int]:
        """Adiciona créditos a um usuário"""
        if amount <= 0:
            return {"success": False, "error": "Quantidade inválida"}, 400

        user_credits = UserCreditsRepository.add_credits(user_id, amount, source)

        CreditTransactionRepository.create(
            {
                "user_id": user_id,
                "transaction_type": source,
                "amount": amount,
                "description": description,
            }
        )

        db.session.commit()

        return {
            "success": True,
            "new_balance": user_credits.balance,
            "message": f"{amount} créditos adicionados!",
        }, 200


class CreditsDashboardService:
    """Serviço para dashboard de créditos"""

    @staticmethod
    def get_dashboard_data(user) -> dict[str, Any]:
        """Obtém dados para o dashboard de créditos"""
        user_credits = CreditsService.get_user_credits(user.id)
        packages = CreditPackageRepository.get_all_active()
        transactions = CreditTransactionRepository.get_by_user(user.id)
        total_generations = AIGenerationRepository.count_by_user(user.id)

        return {
            "credits": user_credits,
            "packages": packages,
            "transactions": transactions,
            "total_generations": total_generations,
            "credit_costs": CREDIT_COSTS,
        }

    @staticmethod
    def get_transactions_paginated(user_id: int, page: int = 1):
        """Obtém transações paginadas"""
        return CreditTransactionRepository.get_by_user_paginated(user_id, page, 50)

    @staticmethod
    def get_generations_paginated(user_id: int, page: int = 1):
        """Obtém gerações paginadas"""
        return AIGenerationRepository.get_by_user_paginated(user_id, page, 20)


class AIGenerationService:
    """Serviço para geração de conteúdo com IA"""

    FUNDAMENTOS_SECTIONS = {
        "direito",
        "fundamentos",
        "fundamentacao",
        "fundamentacao-juridica",
        "fundamentos-juridicos",
        "do-direito",
        "dos-fundamentos",
    }

    @staticmethod
    def is_configured() -> bool:
        """Verifica se o serviço de IA está configurado"""
        return ai_service.is_configured()

    @staticmethod
    def generate_section(
        user,
        section_type: str,
        petition_type: str,
        context: dict,
        existing_content: str = "",
        premium: bool = False,
    ) -> tuple[dict, int]:
        """Gera uma seção de petição"""
        if not AIGenerationService.is_configured():
            return {
                "success": False,
                "error": "Serviço de IA não configurado. Entre em contato com o suporte.",
            }, 503

        # Verifica se é fundamentação
        is_fundamentos = (
            section_type.lower().replace("_", "-")
            in AIGenerationService.FUNDAMENTOS_SECTIONS
        )
        generation_type = "fundamentos" if is_fundamentos else "section"
        credit_cost = ai_service.get_credit_cost(generation_type)

        # Fundamentação sempre usa premium
        if is_fundamentos:
            premium = True

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            user_credits = CreditsService.get_user_credits(user.id)
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }, 402

        try:
            context["petition_type"] = petition_type
            content, metadata = ai_service.generate_section(
                section_type=section_type,
                context=context,
                existing_content=existing_content,
                premium=premium,
            )

            is_master = CreditsService.is_master_user(user)
            actual_cost = 0 if is_master else credit_cost

            if not is_master:
                CreditsService.use_credits_if_needed(user, credit_cost)

            user_credits = CreditsService.get_user_credits(user.id)

            generation = AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": generation_type,
                    "credits_used": actual_cost,
                    "model_used": metadata.get("model", "gpt-4o-mini"),
                    "tokens_input": metadata.get("tokens_input"),
                    "tokens_output": metadata.get("tokens_output"),
                    "tokens_total": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                    "petition_type_slug": petition_type,
                    "section_name": section_type,
                    "input_data": context,
                    "output_content": content,
                    "status": "completed",
                }
            )

            if actual_cost > 0:
                CreditTransactionRepository.create(
                    {
                        "user_id": user.id,
                        "transaction_type": "usage",
                        "amount": -actual_cost,
                        "description": f"Geração de seção: {section_type}",
                        "generation_id": generation.id,
                    }
                )

            db.session.commit()

            return {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance if not is_master else "∞",
                "metadata": {
                    "model": metadata.get("model"),
                    "tokens_used": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                },
            }, 200

        except Exception as e:
            db.session.rollback()
            AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": generation_type,
                    "credits_used": 0,
                    "petition_type_slug": petition_type,
                    "section_name": section_type,
                    "status": "failed",
                    "error_message": str(e),
                }
            )
            db.session.commit()

            return {"success": False, "error": f"Erro ao gerar conteúdo: {str(e)}"}, 500

    @staticmethod
    def generate_full_petition(
        user, petition_type: str, context: dict, premium: bool = True
    ) -> tuple[dict, int]:
        """Gera uma petição completa"""
        if not AIGenerationService.is_configured():
            return {
                "success": False,
                "error": "Serviço de IA não configurado.",
            }, 503

        credit_cost = ai_service.get_credit_cost("full_petition")

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            user_credits = CreditsService.get_user_credits(user.id)
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }, 402

        try:
            content, metadata = ai_service.generate_full_petition(
                petition_type=petition_type, context=context, premium=premium
            )

            is_master = CreditsService.is_master_user(user)
            actual_cost = 0 if is_master else credit_cost

            if not is_master:
                CreditsService.use_credits_if_needed(user, credit_cost)

            user_credits = CreditsService.get_user_credits(user.id)

            generation = AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "full_petition",
                    "credits_used": actual_cost,
                    "model_used": metadata.get("model", "gpt-4o"),
                    "tokens_input": metadata.get("tokens_input"),
                    "tokens_output": metadata.get("tokens_output"),
                    "tokens_total": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                    "petition_type_slug": petition_type,
                    "input_data": context,
                    "output_content": content,
                    "status": "completed",
                }
            )

            if actual_cost > 0:
                CreditTransactionRepository.create(
                    {
                        "user_id": user.id,
                        "transaction_type": "usage",
                        "amount": -actual_cost,
                        "description": f"Geração de petição completa: {petition_type}",
                        "generation_id": generation.id,
                    }
                )

            db.session.commit()

            return {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance if not is_master else "∞",
                "metadata": {
                    "model": metadata.get("model"),
                    "tokens_used": metadata.get("tokens_total"),
                    "response_time_ms": metadata.get("response_time_ms"),
                },
            }, 200

        except Exception as e:
            db.session.rollback()
            AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "full_petition",
                    "credits_used": 0,
                    "petition_type_slug": petition_type,
                    "status": "failed",
                    "error_message": str(e),
                }
            )
            db.session.commit()

            return {"success": False, "error": f"Erro ao gerar petição: {str(e)}"}, 500

    @staticmethod
    def improve_text(
        user, text: str, context: str = "", premium: bool = False
    ) -> tuple[dict, int]:
        """Melhora um texto existente"""
        if not AIGenerationService.is_configured():
            return {"success": False, "error": "Serviço de IA não configurado."}, 503

        if not text or len(text.strip()) < 10:
            return {"success": False, "error": "Texto muito curto para melhorar"}, 400

        credit_cost = ai_service.get_credit_cost("improve")

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            user_credits = CreditsService.get_user_credits(user.id)
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
                "credits_available": user_credits.balance,
            }, 402

        try:
            content, metadata = ai_service.improve_text(
                text=text, context=context, premium=premium
            )

            is_master = CreditsService.is_master_user(user)
            actual_cost = 0 if is_master else credit_cost

            if not is_master:
                CreditsService.use_credits_if_needed(user, credit_cost)

            user_credits = CreditsService.get_user_credits(user.id)

            generation = AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "improve",
                    "credits_used": actual_cost,
                    "model_used": metadata.get("model", "gpt-4o-mini"),
                    "tokens_input": metadata.get("tokens_input"),
                    "tokens_output": metadata.get("tokens_output"),
                    "tokens_total": metadata.get("tokens_total"),
                    "input_data": {"text": text[:500], "context": context},
                    "output_content": content,
                    "status": "completed",
                }
            )

            if actual_cost > 0:
                CreditTransactionRepository.create(
                    {
                        "user_id": user.id,
                        "transaction_type": "usage",
                        "amount": -actual_cost,
                        "description": "Melhoria de texto",
                        "generation_id": generation.id,
                    }
                )

            db.session.commit()

            return {
                "success": True,
                "content": content,
                "credits_used": actual_cost,
                "credits_remaining": user_credits.balance if not is_master else "∞",
            }, 200

        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": f"Erro ao melhorar texto: {str(e)}"}, 500

    @staticmethod
    def submit_feedback(
        user_id: int, generation_id: int, data: dict
    ) -> tuple[dict, int]:
        """Registra feedback sobre uma geração"""
        generation = AIGenerationRepository.get_by_id(generation_id, user_id)
        if not generation:
            return {"error": "Geração não encontrada"}, 404

        AIGenerationRepository.update_feedback(
            generation,
            rating=data.get("rating"),
            was_used=data.get("was_used"),
        )

        return {"success": True}, 200


class DocumentAnalysisService:
    """Serviço para análise de documentos com IA"""

    @staticmethod
    def analyze_document(user, file) -> tuple[dict, int]:
        """Analisa um documento com IA"""
        credit_cost = CREDIT_COSTS.get("analyze_document", 4)

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
            }, 402

        is_valid, error_msg = validate_document_file(file)
        if not is_valid:
            return {"success": False, "error": error_msg}, 400

        try:
            document_text, doc_metadata = extract_document_text(file)

            if not document_text or len(document_text.strip()) < 50:
                return {
                    "success": False,
                    "error": "Não foi possível extrair texto suficiente do documento",
                }, 400

            analysis, ai_metadata = ai_service.analyze_document(
                document_text, file.filename
            )

            if not CreditsService.is_master_user(user):
                CreditsService.use_credits_if_needed(user, credit_cost)

            # Salvar na sessão para uso posterior
            session["last_document_text"] = document_text[:20000]
            session["last_document_analysis"] = analysis
            session["last_document_name"] = file.filename

            AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "analyze_document",
                    "prompt": f"Análise de: {file.filename}",
                    "result": analysis[:5000],
                    "tokens_used": ai_metadata.get("tokens_total", 0),
                    "model_used": ai_metadata.get("model", "gpt-4o"),
                    "credits_used": credit_cost,
                    "status": "completed",
                }
            )
            db.session.commit()

            return {
                "success": True,
                "analysis": analysis,
                "document_info": doc_metadata,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }, 200

        except Exception as e:
            current_app.logger.error(f"Erro ao analisar documento: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao processar documento: {str(e)}",
            }, 500

    @staticmethod
    def generate_fundamentos(user, data: dict) -> tuple[dict, int]:
        """Gera fundamentação jurídica baseada em documento"""
        credit_cost = CREDIT_COSTS.get("fundamentos", 3)

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_required": credit_cost,
            }, 402

        document_text = data.get("document_text") or session.get("last_document_text")
        document_analysis = data.get("document_analysis") or session.get(
            "last_document_analysis"
        )

        if not document_text and not document_analysis:
            return {
                "success": False,
                "error": "Nenhum documento carregado. Faça upload e análise primeiro.",
            }, 400

        try:
            fundamentos, ai_metadata = ai_service.generate_fundamentos_from_document(
                document_text=document_text,
                document_analysis=document_analysis,
                petition_type=data.get("petition_type"),
                additional_context=data.get("additional_context"),
            )

            if not CreditsService.is_master_user(user):
                CreditsService.use_credits_if_needed(user, credit_cost)

            AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "fundamentos",
                    "prompt": "Fundamentação baseada em documento",
                    "result": fundamentos[:5000],
                    "tokens_used": ai_metadata.get("tokens_total", 0),
                    "model_used": ai_metadata.get("model", "gpt-4o"),
                    "credits_used": credit_cost,
                    "status": "completed",
                }
            )
            db.session.commit()

            return {
                "success": True,
                "fundamentos": fundamentos,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }, 200

        except Exception as e:
            current_app.logger.error(f"Erro ao gerar fundamentação: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao gerar fundamentação: {str(e)}",
            }, 500


class RiskAnalysisService:
    """Serviço para análise de riscos com IA"""

    @staticmethod
    def analyze_risk(user, data: dict) -> tuple[dict, int]:
        """Analisa riscos e chances de êxito de uma petição"""
        from app.services.ai_service import get_credit_cost

        credit_cost = get_credit_cost("analyze_risk")

        if not CreditsService.has_sufficient_credits(user, credit_cost):
            return {
                "success": False,
                "error": "Créditos insuficientes",
                "credits_needed": credit_cost,
            }, 402

        if not ai_service.is_configured():
            return {"success": False, "error": "API de IA não configurada"}, 503

        petition_content = data.get("petition_content", "")
        petition_type = data.get("petition_type", "")
        fatos = data.get("fatos", "")
        pedidos = data.get("pedidos", "")
        fundamentacao = data.get("fundamentacao", "")

        if not petition_content and not (fatos or pedidos or fundamentacao):
            return {
                "success": False,
                "error": "Forneça o conteúdo da petição ou as seções individuais",
            }, 400

        try:
            analysis_json, ai_metadata = ai_service.analyze_risk(
                petition_content=petition_content,
                petition_type=petition_type,
                fatos=fatos,
                pedidos=pedidos,
                fundamentacao=fundamentacao,
            )

            if not CreditsService.use_credits_if_needed(user, credit_cost):
                return {"success": False, "error": "Erro ao debitar créditos"}, 500

            # Parsear JSON
            try:
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
                analysis = {"raw_analysis": analysis_json, "parse_error": True}

            CreditTransactionRepository.create(
                {
                    "user_id": user.id,
                    "transaction_type": "usage",
                    "amount": -credit_cost,
                    "description": f"Análise de riscos: {petition_type or 'Petição'}",
                }
            )

            AIGenerationRepository.create(
                {
                    "user_id": user.id,
                    "generation_type": "analyze_risk",
                    "credits_used": credit_cost,
                    "input_data": {"petition_type": petition_type},
                    "output_content": str(analysis)[:5000],
                    "model_used": ai_metadata.get("model", "gpt-4o"),
                    "status": "completed",
                }
            )

            db.session.commit()

            return {
                "success": True,
                "analysis": analysis,
                "ai_info": {
                    "model": ai_metadata.get("model"),
                    "tokens": ai_metadata.get("tokens_total"),
                },
                "credits_used": credit_cost,
            }, 200

        except Exception as e:
            current_app.logger.error(f"Erro ao analisar riscos: {str(e)}")
            return {
                "success": False,
                "error": f"Erro ao analisar petição: {str(e)}",
            }, 500


class PaymentService:
    """Serviço para pagamentos de créditos"""

    @staticmethod
    def create_checkout_preference(
        user, package_slug: str, host_url: str
    ) -> tuple[dict, int]:
        """Cria preferência de pagamento no Mercado Pago"""
        package = CreditPackageRepository.get_by_slug(package_slug)
        if not package:
            return {"error": "Pacote não encontrado"}, 404

        mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not mp_access_token:
            return {"error": "Mercado Pago não configurado"}, 500

        mp_sdk = mercadopago.SDK(mp_access_token)

        success_url = host_url.rstrip("/") + url_for(
            "ai.credits_success", package_id=package.id
        )
        failure_url = host_url.rstrip("/") + url_for("ai.credits_failure")
        pending_url = host_url.rstrip("/") + url_for("ai.credits_pending")

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
                "name": user.full_name or user.username,
                "email": user.email,
            },
            "back_urls": {
                "success": success_url,
                "failure": failure_url,
                "pending": pending_url,
            },
            "auto_return": "approved",
            "external_reference": f"credits_{user.id}_{package.id}",
            "metadata": {
                "user_id": user.id,
                "package_id": package.id,
                "credits": package.credits,
                "bonus_credits": package.bonus_credits or 0,
            },
        }

        try:
            preference_response = mp_sdk.preference().create(preference_data)
            preference = preference_response["response"]

            return {
                "success": True,
                "init_point": preference["init_point"],
                "preference_id": preference["id"],
            }, 200

        except Exception as e:
            current_app.logger.error(f"Erro ao criar preferência MP: {str(e)}")
            return {"error": "Erro ao processar pagamento"}, 500

    @staticmethod
    def create_pix_payment(user, package_slug: str) -> tuple[dict, int]:
        """Cria pagamento PIX para créditos"""
        package = CreditPackageRepository.get_by_slug(package_slug)
        if not package:
            return {"error": "Pacote não encontrado"}, 404

        mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not mp_access_token:
            return {"error": "Mercado Pago não configurado"}, 500

        mp_sdk = mercadopago.SDK(mp_access_token)

        payment_data = {
            "transaction_amount": float(package.price),
            "description": f"{package.name} - {package.total_credits} créditos de IA",
            "payment_method_id": "pix",
            "payer": {
                "email": user.email,
                "first_name": user.full_name.split()[0]
                if user.full_name
                else user.username,
                "last_name": user.full_name.split()[-1]
                if user.full_name and len(user.full_name.split()) > 1
                else "",
            },
            "metadata": {
                "user_id": user.id,
                "package_id": package.id,
                "credits": package.credits,
                "bonus_credits": package.bonus_credits or 0,
                "type": "credit_purchase",
            },
            "external_reference": f"credits_pix_{user.id}_{package.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        }

        try:
            payment_response = mp_sdk.payment().create(payment_data)
            payment = payment_response["response"]

            if payment.get("status") == "pending":
                pix_data = payment.get("point_of_interaction", {}).get(
                    "transaction_data", {}
                )
                return {
                    "success": True,
                    "payment_id": payment["id"],
                    "qr_code": pix_data.get("qr_code"),
                    "qr_code_base64": pix_data.get("qr_code_base64"),
                    "expiration": payment.get("date_of_expiration"),
                }, 200
            else:
                return {
                    "error": f"Erro ao criar PIX: {payment.get('status_detail', 'unknown')}"
                }, 400

        except Exception as e:
            current_app.logger.error(f"Erro ao criar PIX de créditos: {str(e)}")
            return {"error": "Erro ao processar pagamento PIX"}, 500

    @staticmethod
    def check_pix_status(user_id: int, payment_id: int) -> tuple[dict, int]:
        """Verifica status do pagamento PIX"""
        mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
        if not mp_access_token:
            return {"error": "Mercado Pago não configurado"}, 500

        mp_sdk = mercadopago.SDK(mp_access_token)

        try:
            payment_response = mp_sdk.payment().get(payment_id)
            payment = payment_response["response"]

            status = payment.get("status")

            if status == "approved":
                metadata = payment.get("metadata", {})
                if metadata.get("user_id") == user_id and metadata.get("package_id"):
                    existing = CreditTransactionRepository.get_by_payment_id(
                        str(payment_id)
                    )
                    if not existing:
                        PaymentService._process_credit_purchase(
                            payment_id, user_id, metadata.get("package_id"), metadata
                        )

            return {
                "success": True,
                "status": status,
                "status_detail": payment.get("status_detail"),
            }, 200

        except Exception as e:
            current_app.logger.error(f"Erro ao verificar PIX: {str(e)}")
            return {"error": "Erro ao verificar pagamento"}, 500

    @staticmethod
    def _process_credit_purchase(
        payment_id: int, user_id: int, package_id: int, metadata: dict
    ) -> bool:
        """Processa compra de créditos após pagamento aprovado"""
        try:
            package = CreditPackageRepository.get_by_id(package_id)
            if not package:
                return False

            credits_to_add = metadata.get("credits", package.credits)
            bonus_to_add = metadata.get("bonus_credits", package.bonus_credits or 0)

            UserCreditsRepository.add_credits(user_id, credits_to_add, "purchase")
            if bonus_to_add > 0:
                UserCreditsRepository.add_credits(user_id, bonus_to_add, "bonus")

            # Credits updated via repository

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

            db.session.commit()

            current_app.logger.info(
                f"✅ Créditos PIX processados: user={user_id}, credits={credits_to_add}, bonus={bonus_to_add}"
            )
            return True

        except Exception as e:
            current_app.logger.error(f"Erro ao processar compra de créditos: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def process_success_callback(user, package_id: int, payment_id: str | None) -> dict:
        """Processa callback de sucesso do pagamento"""
        package = CreditPackageRepository.get_by_id(package_id)
        if not package:
            return {"package": None}

        if payment_id:
            UserCreditsRepository.add_credits(user.id, package.credits, "purchase")

            if package.bonus_credits:
                UserCreditsRepository.add_credits(
                    user.id, package.bonus_credits, "bonus"
                )

            CreditTransactionRepository.create(
                {
                    "user_id": user.id,
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
                        "user_id": user.id,
                        "transaction_type": "bonus",
                        "amount": package.bonus_credits,
                        "description": f"Bônus de {package.name}",
                        "package_id": package.id,
                    }
                )

            db.session.commit()

        return {"package": package, "payment_id": payment_id}
