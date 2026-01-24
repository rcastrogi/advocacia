"""
Payments Services - Camada de lógica de negócios
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import mercadopago
from flask import current_app, url_for

# db import removed - using repositories
from app.payments.repository import (
    BalanceRepository,
    BillingPlanPaymentRepository,
    NotificationRepository,
    PaymentRepository,
    SubscriptionRepository,
    UserPaymentRepository,
)
from app.utils.audit import AuditManager

# Configurar Mercado Pago SDK
mp_access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
mp_sdk = mercadopago.SDK(mp_access_token) if mp_access_token else None


class PaymentGatewayService:
    """Serviço para integração com gateway de pagamento"""

    @staticmethod
    def is_configured() -> bool:
        return mp_sdk is not None

    @staticmethod
    def create_pix_payment(
        user, amount: float, description: str
    ) -> dict[str, Any] | None:
        """Cria pagamento PIX no Mercado Pago"""
        if not mp_sdk:
            return None

        payment_data = {
            "transaction_amount": amount,
            "description": description,
            "payment_method_id": "pix",
            "payer": {
                "email": user.email,
                "first_name": user.full_name or user.username,
            },
        }

        result = mp_sdk.payment().create(payment_data)
        if result["status"] != 201:
            return None

        return result["response"]

    @staticmethod
    def create_preapproval(user, plan, amount: float) -> dict[str, Any] | None:
        """Cria assinatura recorrente (preapproval) no Mercado Pago"""
        if not mp_sdk:
            return None

        preapproval_data = {
            "payer_email": user.email,
            "back_url": url_for("payments.success", _external=True),
            "reason": f"Petitio - {plan.name}",
            "external_reference": f"sub_{user.id}_{plan.id}",
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
            return None

        return result["response"]

    @staticmethod
    def get_payment_info(payment_id: str) -> dict[str, Any] | None:
        """Obtém informações de pagamento do Mercado Pago"""
        if not mp_sdk:
            return None

        result = mp_sdk.payment().get(payment_id)
        return result.get("response")

    @staticmethod
    def get_preapproval_info(preapproval_id: str) -> dict[str, Any] | None:
        """Obtém informações de preapproval do Mercado Pago"""
        if not mp_sdk:
            return None

        result = mp_sdk.preapproval().get(preapproval_id)
        return result.get("response")


class WebhookSecurityService:
    """Serviço para validação de webhooks"""

    @staticmethod
    def validate_mercadopago_signature(request_data: dict, headers: dict) -> bool:
        """Valida a assinatura do webhook do Mercado Pago"""
        try:
            webhook_secret = current_app.config.get("MERCADOPAGO_WEBHOOK_SECRET")
            if not webhook_secret:
                current_app.logger.warning("MERCADOPAGO_WEBHOOK_SECRET não configurado")
                return False

            x_signature = headers.get("x-signature")
            x_request_id = headers.get("x-request-id")

            if not x_signature or not x_request_id:
                current_app.logger.warning("Headers x-signature ou x-request-id ausentes")
                return False

            # Parse x-signature
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

            # Criar template para assinatura
            data_id = str(request_data.get("data", {}).get("id", "")).lower()
            template = f"id:{data_id};request-id:{x_request_id};ts:{ts};"

            # Calcular assinatura esperada
            expected_signature = hmac.new(
                webhook_secret.encode("utf-8"),
                template.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            current_app.logger.error(f"Erro na validação da assinatura: {str(e)}")
            return False


class PIXPaymentService:
    """Serviço para pagamentos PIX"""

    @staticmethod
    def create_payment(
        user, amount: float, plan=None, billing_period: str = "1m"
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Cria pagamento PIX"""
        description = "Pagamento via PIX"

        if plan:
            if not plan.active:
                return None, "Plano inválido ou inativo"
            if plan.plan_type != "per_usage":
                return None, "PIX disponível apenas para planos pay-per-use"
            amount = max(amount, float(plan.monthly_fee))
            description = f"Petitio - {plan.name} ({billing_period})"

        # Criar no gateway
        gateway_response = PaymentGatewayService.create_pix_payment(
            user, amount, description
        )

        if not gateway_response:
            return None, "Erro ao criar pagamento"

        # Salvar no banco
        payment = PaymentRepository.create({
            "user_id": user.id,
            "amount": Decimal(str(amount)),
            "payment_type": "one_time",
            "payment_method": "pix",
            "status": "pending",
            "gateway": "mercadopago",
            "gateway_payment_id": str(gateway_response["id"]),
            "description": description,
            "pix_code": gateway_response["point_of_interaction"]["transaction_data"]["qr_code"],
            "pix_qr_code": gateway_response["point_of_interaction"]["transaction_data"]["qr_code_base64"],
            "pix_expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        })

        AuditManager.log_payment_created(payment, user)

        return {
            "payment_id": payment.id,
            "pix_code": payment.pix_code,
            "pix_qr_code": payment.pix_qr_code,
            "expires_at": payment.pix_expires_at.isoformat(),
        }, None


class SubscriptionService:
    """Serviço para assinaturas"""

    @staticmethod
    def get_plans():
        """Carrega planos ativos"""
        return BillingPlanPaymentRepository.get_active_plans()

    @staticmethod
    def get_user_subscription(user):
        """Obtém assinatura atual do usuário"""
        return SubscriptionRepository.get_active_by_user(user.id)

    @staticmethod
    def get_latest_subscription(user):
        """Obtém última assinatura do usuário"""
        return SubscriptionRepository.get_latest_by_user(user.id)

    @staticmethod
    def validate_subscription_request(
        plan_slug: str, billing_period: str
    ) -> tuple[Any | None, str | None]:
        """Valida requisição de assinatura"""
        plan = BillingPlanPaymentRepository.get_by_slug(plan_slug)
        if not plan:
            return None, "Plano inválido"

        valid_periods = ["1m", "3m", "6m", "1y", "2y", "3y"]
        if billing_period not in valid_periods:
            return None, "Período de cobrança inválido"

        if billing_period not in plan.supported_periods:
            return None, "Este plano não suporta o período selecionado"

        amount = plan.get_price_for_period(billing_period)
        if amount is None:
            return None, "Erro ao calcular preço"

        return {
            "plan": plan,
            "amount": amount,
            "period_label": plan.get_period_label(billing_period),
        }, None

    @staticmethod
    def create_subscription(
        user, plan, billing_period: str = "monthly"
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Cria assinatura recorrente"""
        if plan.plan_type == "per_usage":
            return None, "Preapproval disponível apenas para assinaturas"

        amount = float(plan.monthly_fee)

        # Criar no gateway
        gateway_response = PaymentGatewayService.create_preapproval(user, plan, amount)
        if not gateway_response:
            return None, "Erro ao criar assinatura"

        # Salvar no banco
        subscription = SubscriptionRepository.create({
            "user_id": user.id,
            "plan_type": plan.plan_type,
            "billing_period": billing_period,
            "amount": Decimal(str(amount)),
            "status": "pending",
            "gateway": "mercadopago",
            "gateway_subscription_id": gateway_response["id"],
        })

        AuditManager.log_subscription_created(subscription, user)

        return {
            "preapproval_url": gateway_response["init_point"],
            "preapproval_id": gateway_response["id"],
        }, None

    @staticmethod
    def cancel_subscription(user, immediate: bool = False, reason: str = None) -> tuple[bool, str | None]:
        """Cancela assinatura do usuário"""
        subscription = SubscriptionRepository.get_active_by_user(user.id)
        if not subscription:
            return False, "Assinatura não encontrada"

        subscription.cancel(immediate=immediate)
        AuditManager.log_subscription_cancelled(
            subscription, reason=reason or "Solicitado pelo usuário", immediate=immediate
        )

        return True, None


class WebhookProcessorService:
    """Serviço para processamento de webhooks"""

    @staticmethod
    def process_payment_webhook(payment_id: str) -> None:
        """Processa webhook de pagamento único"""
        payment_data = PaymentGatewayService.get_payment_info(payment_id)
        if not payment_data:
            return

        if payment_data["status"] == "approved":
            payment = PaymentRepository.get_by_gateway_id(str(payment_id))
            if not payment:
                payment = PaymentRepository.get_by_external_id(str(payment_id))

            if payment and payment.status == "pending":
                PaymentRepository.mark_as_paid(payment)

                extra_data = payment.extra_data or {}
                if extra_data.get("type") == "balance_deposit":
                    BalanceDepositService.process_deposit(payment)
                else:
                    if payment.payment_type == "one_time":
                        user = UserPaymentRepository.get_by_id(payment.user_id)
                        UserPaymentRepository.update_billing_status(user, "active")

                # Processar referral
                ReferralConversionService.process(payment.user_id, payment.id, payment.amount)

                AuditManager.log_payment_completed(payment)
                current_app.logger.info(f"✅ Pagamento aprovado: {payment_id}")

        elif payment_data["status"] in ["rejected", "cancelled"]:
            payment = PaymentRepository.get_by_gateway_id(str(payment_id))
            if not payment:
                payment = PaymentRepository.get_by_external_id(str(payment_id))

            if payment and payment.status == "pending":
                PaymentRepository.update_status(payment, "failed")
                AuditManager.log_payment_failed(payment, f"Status: {payment_data['status']}")

    @staticmethod
    def process_preapproval_webhook(preapproval_id: str) -> None:
        """Processa webhook de preapproval (assinatura)"""
        preapproval_data = PaymentGatewayService.get_preapproval_info(preapproval_id)
        if not preapproval_data:
            return

        subscription = SubscriptionRepository.get_by_gateway_id(str(preapproval_id))
        if not subscription:
            current_app.logger.warning(f"Preapproval não encontrado: {preapproval_id}")
            return

        old_status = subscription.status
        status = preapproval_data["status"]

        if status == "authorized":
            SubscriptionRepository.activate(subscription, subscription.billing_period)
            user = UserPaymentRepository.get_by_id(subscription.user_id)
            UserPaymentRepository.update_billing_status(user, "active")

            ReferralConversionService.process(subscription.user_id, None, subscription.price)
            AuditManager.log_subscription_activated(subscription)
            current_app.logger.info(f"✅ Assinatura ativada: {preapproval_id}")

        elif status == "cancelled":
            SubscriptionRepository.cancel(subscription)
            user = UserPaymentRepository.get_by_id(subscription.user_id)
            if SubscriptionRepository.count_active_by_user(user.id) == 0:
                UserPaymentRepository.update_billing_status(user, "inactive")

            AuditManager.log_subscription_cancelled(subscription, reason="Cancelamento via gateway")
            current_app.logger.info(f"❌ Assinatura cancelada: {preapproval_id}")

        elif status == "paused":
            SubscriptionRepository.update_status(subscription, "paused")
            user = UserPaymentRepository.get_by_id(subscription.user_id)
            UserPaymentRepository.update_billing_status(user, "inactive")

            AuditManager.log_subscription_status_change(subscription, old_status, "paused", "Pausada via gateway")
            current_app.logger.warning(f"⏸️ Assinatura pausada: {preapproval_id}")

        elif status == "expired":
            SubscriptionRepository.update_status(subscription, "expired")
            user = UserPaymentRepository.get_by_id(subscription.user_id)
            UserPaymentRepository.update_billing_status(user, "inactive")

            AuditManager.log_subscription_status_change(subscription, old_status, "expired", "Expirada")
            current_app.logger.warning(f"⏰ Assinatura expirada: {preapproval_id}")


class BalanceDepositService:
    """Serviço para depósitos de saldo"""

    @staticmethod
    def create_pix_deposit(
        user, amount: Decimal
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Cria pagamento PIX para depósito de saldo"""
        if not PaymentGatewayService.is_configured():
            return None, "Sistema de pagamento não configurado"

        if amount < Decimal("10.00"):
            return None, "Valor mínimo para depósito é R$ 10,00"
        if amount > Decimal("10000.00"):
            return None, "Valor máximo para depósito é R$ 10.000,00"

        # Criar no gateway
        gateway_response = PaymentGatewayService.create_pix_payment(
            user, float(amount), "Depósito de saldo - Petitio"
        )

        if not gateway_response:
            return None, "Erro ao criar pagamento PIX"

        # Salvar no banco
        payment = PaymentRepository.create({
            "user_id": user.id,
            "external_id": str(gateway_response["id"]),
            "payment_method": "pix",
            "amount": amount,
            "status": "pending",
            "description": "Depósito de saldo para petições",
            "pix_code": gateway_response["point_of_interaction"]["transaction_data"]["qr_code"],
            "pix_qr_code": gateway_response["point_of_interaction"]["transaction_data"]["qr_code_base64"],
            "pix_expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "extra_data": {"type": "balance_deposit", "mp_response": gateway_response},
        })

        return {
            "payment_id": payment.id,
            "pix_code": payment.pix_code,
            "pix_qr_code": payment.pix_qr_code,
            "expires_at": payment.pix_expires_at.isoformat(),
            "amount": float(amount),
        }, None

    @staticmethod
    def process_deposit(payment) -> bool:
        """Processa depósito de saldo quando pagamento PIX é confirmado"""
        from app.billing.utils import add_petition_balance

        extra_data = payment.extra_data or {}

        if extra_data.get("balance_credited"):
            current_app.logger.info(f"Depósito já processado: payment={payment.id}")
            return True

        try:
            user = UserPaymentRepository.get_by_id(payment.user_id)
            if not user:
                current_app.logger.error(f"Usuário não encontrado: {payment.user_id}")
                return False

            balance = add_petition_balance(
                user, payment.amount, source="deposit", payment_id=payment.id
            )

            PaymentRepository.update_extra_data(payment, {"balance_credited": True})

            current_app.logger.info(
                f"✅ Depósito processado: user={payment.user_id}, "
                f"amount=R${payment.amount}, new_balance=R${balance.balance}"
            )

            # Criar notificação
            try:
                NotificationRepository.create({
                    "user_id": user.id,
                    "type": "payment",
                    "title": "Depósito confirmado!",
                    "message": f"Seu depósito de R$ {payment.amount:.2f} foi confirmado. Saldo atual: R$ {balance.balance:.2f}",
                    "data": {"payment_id": payment.id, "amount": float(payment.amount)},
                })
            except Exception as e:
                current_app.logger.warning(f"Erro ao criar notificação: {e}")

            return True

        except Exception as e:
            current_app.logger.error(f"Erro ao processar depósito: {str(e)}")
            return False


class BalanceDashboardService:
    """Serviço para dashboard de saldo"""

    @staticmethod
    def get_balance_info(user) -> dict[str, Any]:
        """Obtém informações de saldo do usuário"""
        from app.billing.utils import get_user_petition_balance

        balance_info = get_user_petition_balance(user)
        transactions = BalanceRepository.get_transactions(user.id)

        return {
            "balance": balance_info,
            "transactions": transactions,
        }

    @staticmethod
    def get_transactions_paginated(user, page: int = 1, per_page: int = 20):
        """Obtém transações paginadas"""
        return BalanceRepository.get_transactions_paginated(user.id, page, per_page)


class ReferralConversionService:
    """Serviço para conversão de indicações"""

    @staticmethod
    def process(user_id: int, payment_id: int | None, payment_amount) -> None:
        """Processa conversão de indicação quando pagamento é confirmado"""
        try:
            from app.referral.routes import process_referral_conversion

            referral = process_referral_conversion(user_id, payment_id, payment_amount)
            if referral and referral.reward_granted:
                current_app.logger.info(
                    f"🎁 Referral conversion: user={user_id}, referrer={referral.referrer_id}, "
                    f"credits={referral.referrer_reward_credits}+{referral.referred_reward_credits}"
                )
        except Exception as e:
            current_app.logger.error(f"Erro ao processar indicação: {str(e)}")
