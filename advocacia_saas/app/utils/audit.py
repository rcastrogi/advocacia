"""
Sistema de Auditoria para rastreamento de alterações
Registra todas as modificações importantes no sistema
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import request, session
from flask_login import current_user

from app import db
from app.models import AuditLog


class AuditManager:
    """Gerenciador de auditoria para o sistema"""

    @staticmethod
    def log_change(
        entity_type: str,
        entity_id: int,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        changed_fields: List[str] = None,
        description: str = None,
        additional_metadata: Dict = None,
        user_id: int = None,
    ):
        """
        Registra uma alteração no log de auditoria

        Args:
            entity_type: Tipo da entidade ('user', 'client', 'petition', etc.)
            entity_id: ID da entidade afetada
            action: Tipo da ação ('create', 'update', 'delete', 'login', 'logout')
            old_values: Valores antigos (para updates)
            new_values: Valores novos (para updates/creates)
            changed_fields: Lista de campos alterados
            description: Descrição da alteração
            metadata: Dados adicionais
            user_id: ID do usuário que fez a alteração (opcional, usa current_user se None)
        """

        # Usar current_user se user_id não fornecido
        if user_id is None and current_user and current_user.is_authenticated:
            user_id = current_user.id

        # Obter informações da requisição
        ip_address = AuditManager._get_client_ip()
        user_agent = AuditManager._get_user_agent()
        session_id = AuditManager._get_session_id()

        # Criar log de auditoria
        audit_log = AuditLog(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            description=description,
            additional_metadata=additional_metadata,
        )

        try:
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            # Log do erro mas não falha a operação principal
            print(f"Erro ao registrar log de auditoria: {e}")
            db.session.rollback()

    @staticmethod
    def log_user_change(
        user,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        changed_fields: List[str] = None,
    ):
        """Registra alteração em usuário"""
        description = f"Usuário {user.email} - {action}"
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            description=description,
        )

    @staticmethod
    def log_client_change(
        client,
        action: str,
        old_values: Dict = None,
        new_values: Dict = None,
        changed_fields: List[str] = None,
    ):
        """Registra alteração em cliente"""
        description = f"Cliente {client.full_name} - {action}"
        AuditManager.log_change(
            entity_type="client",
            entity_id=client.id,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            description=description,
        )

    @staticmethod
    def log_login(user, success: bool = True):
        """Registra tentativa de login"""
        action = "login_success" if success else "login_failed"
        description = f"Login {'bem-sucedido' if success else 'falhou'} - {user.email}"
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action=action,
            description=description,
            additional_metadata={"login_success": success},
        )

    @staticmethod
    def log_logout(user):
        """Registra logout"""
        description = f"Logout - {user.email}"
        AuditManager.log_change(
            entity_type="user",
            entity_id=user.id,
            action="logout",
            description=description,
        )

    # =========================================================================
    # AUDITORIA DE PAGAMENTOS E ASSINATURAS
    # =========================================================================

    @staticmethod
    def log_payment_created(payment, user=None):
        """Registra criação de pagamento"""
        user_email = user.email if user else "N/A"
        description = (
            f"Pagamento criado - {payment.payment_method} - R$ {payment.amount}"
        )
        AuditManager.log_change(
            entity_type="payment",
            entity_id=payment.id,
            action="payment_created",
            new_values={
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_method": payment.payment_method,
                "payment_type": payment.payment_type,
                "gateway": payment.gateway,
                "gateway_payment_id": payment.gateway_payment_id,
                "status": payment.status,
            },
            description=description,
            additional_metadata={
                "user_email": user_email,
                "gateway": payment.gateway,
            },
            user_id=payment.user_id,
        )

    @staticmethod
    def log_payment_status_change(payment, old_status, new_status, reason=None):
        """Registra mudança de status do pagamento"""
        description = f"Status do pagamento alterado: {old_status} → {new_status}"
        if reason:
            description += f" ({reason})"
        AuditManager.log_change(
            entity_type="payment",
            entity_id=payment.id,
            action="payment_status_changed",
            old_values={"status": old_status},
            new_values={"status": new_status},
            changed_fields=["status"],
            description=description,
            additional_metadata={
                "reason": reason,
                "gateway_payment_id": payment.gateway_payment_id,
            },
            user_id=payment.user_id,
        )

    @staticmethod
    def log_payment_completed(payment):
        """Registra pagamento concluído/aprovado"""
        description = (
            f"Pagamento aprovado - R$ {payment.amount} via {payment.payment_method}"
        )
        AuditManager.log_change(
            entity_type="payment",
            entity_id=payment.id,
            action="payment_completed",
            new_values={
                "status": "completed",
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
            },
            description=description,
            additional_metadata={
                "gateway": payment.gateway,
                "gateway_payment_id": payment.gateway_payment_id,
                "amount": str(payment.amount),
            },
            user_id=payment.user_id,
        )

    @staticmethod
    def log_payment_failed(payment, error_message=None):
        """Registra falha no pagamento"""
        description = f"Pagamento falhou - R$ {payment.amount}"
        if error_message:
            description += f" - {error_message}"
        AuditManager.log_change(
            entity_type="payment",
            entity_id=payment.id,
            action="payment_failed",
            new_values={"status": "failed"},
            description=description,
            additional_metadata={
                "error_message": error_message,
                "gateway": payment.gateway,
            },
            user_id=payment.user_id,
        )

    @staticmethod
    def log_payment_refunded(payment, refund_amount, reason=None):
        """Registra reembolso de pagamento"""
        description = f"Reembolso processado - R$ {refund_amount}"
        if reason:
            description += f" - Motivo: {reason}"
        AuditManager.log_change(
            entity_type="payment",
            entity_id=payment.id,
            action="payment_refunded",
            old_values={"status": payment.status},
            new_values={"status": "refunded", "refund_amount": str(refund_amount)},
            description=description,
            additional_metadata={
                "refund_amount": str(refund_amount),
                "reason": reason,
                "gateway": payment.gateway,
            },
            user_id=payment.user_id,
        )

    @staticmethod
    def log_subscription_created(subscription, user=None):
        """Registra criação de assinatura"""
        user_email = user.email if user else "N/A"
        description = (
            f"Assinatura criada - {subscription.plan_type} - R$ {subscription.amount}"
        )
        AuditManager.log_change(
            entity_type="subscription",
            entity_id=subscription.id,
            action="subscription_created",
            new_values={
                "plan_type": subscription.plan_type,
                "billing_period": subscription.billing_period,
                "amount": str(subscription.amount),
                "status": subscription.status,
                "gateway": subscription.gateway,
            },
            description=description,
            additional_metadata={
                "user_email": user_email,
                "gateway": subscription.gateway,
            },
            user_id=subscription.user_id,
        )

    @staticmethod
    def log_subscription_activated(subscription):
        """Registra ativação de assinatura"""
        description = f"Assinatura ativada - {subscription.plan_type}"
        AuditManager.log_change(
            entity_type="subscription",
            entity_id=subscription.id,
            action="subscription_activated",
            old_values={"status": "pending"},
            new_values={
                "status": "active",
                "started_at": subscription.started_at.isoformat()
                if subscription.started_at
                else None,
                "renewal_date": subscription.renewal_date.isoformat()
                if subscription.renewal_date
                else None,
            },
            changed_fields=["status", "started_at", "renewal_date"],
            description=description,
            user_id=subscription.user_id,
        )

    @staticmethod
    def log_subscription_cancelled(subscription, reason=None, immediate=False):
        """Registra cancelamento de assinatura"""
        cancel_type = "imediato" if immediate else "ao fim do período"
        description = f"Assinatura cancelada ({cancel_type})"
        if reason:
            description += f" - Motivo: {reason}"
        AuditManager.log_change(
            entity_type="subscription",
            entity_id=subscription.id,
            action="subscription_cancelled",
            old_values={"status": subscription.status},
            new_values={
                "status": "cancelled",
                "cancelled_at": subscription.cancelled_at.isoformat()
                if subscription.cancelled_at
                else None,
            },
            changed_fields=["status", "cancelled_at"],
            description=description,
            additional_metadata={
                "reason": reason,
                "immediate": immediate,
            },
            user_id=subscription.user_id,
        )

    @staticmethod
    def log_subscription_renewed(subscription, old_renewal_date, new_renewal_date):
        """Registra renovação de assinatura"""
        description = f"Assinatura renovada até {new_renewal_date.strftime('%d/%m/%Y')}"
        AuditManager.log_change(
            entity_type="subscription",
            entity_id=subscription.id,
            action="subscription_renewed",
            old_values={
                "renewal_date": old_renewal_date.isoformat()
                if old_renewal_date
                else None
            },
            new_values={"renewal_date": new_renewal_date.isoformat()},
            changed_fields=["renewal_date"],
            description=description,
            user_id=subscription.user_id,
        )

    @staticmethod
    def log_subscription_status_change(
        subscription, old_status, new_status, reason=None
    ):
        """Registra mudança de status da assinatura"""
        description = f"Status da assinatura alterado: {old_status} → {new_status}"
        if reason:
            description += f" ({reason})"
        AuditManager.log_change(
            entity_type="subscription",
            entity_id=subscription.id,
            action="subscription_status_changed",
            old_values={"status": old_status},
            new_values={"status": new_status},
            changed_fields=["status"],
            description=description,
            additional_metadata={"reason": reason},
            user_id=subscription.user_id,
        )

    @staticmethod
    def log_credits_transaction(
        user, transaction_type, amount, balance_before, balance_after, description=None
    ):
        """Registra transação de créditos"""
        desc = description or f"Transação de créditos: {transaction_type}"
        AuditManager.log_change(
            entity_type="credits",
            entity_id=user.id,
            action=f"credits_{transaction_type}",
            old_values={"balance": balance_before},
            new_values={"balance": balance_after},
            changed_fields=["balance"],
            description=desc,
            additional_metadata={
                "transaction_type": transaction_type,
                "amount": amount,
            },
            user_id=user.id,
        )

    @staticmethod
    def get_audit_logs(
        entity_type: str = None,
        entity_id: int = None,
        user_id: int = None,
        action: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Busca logs de auditoria com filtros"""

        query = AuditLog.query

        if entity_type:
            query = query.filter_by(entity_type=entity_type)
        if entity_id:
            query = query.filter_by(entity_id=entity_id)
        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter_by(action=action)

        return (
            query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()
        )

    @staticmethod
    def get_entity_history(entity_type: str, entity_id: int) -> List[AuditLog]:
        """Obtém histórico completo de uma entidade"""
        return (
            AuditLog.query.filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(AuditLog.timestamp.asc())
            .all()
        )

    @staticmethod
    def _get_client_ip() -> Optional[str]:
        """Obtém o IP do cliente"""
        try:
            if request:
                # Verificar headers comuns de proxy
                ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                if not ip:
                    ip = request.headers.get("X-Real-IP", "")
                if not ip:
                    ip = request.remote_addr
                return ip
        except RuntimeError:
            # Fora do contexto de requisição
            pass
        except Exception:
            pass
        return None

    @staticmethod
    def _get_user_agent() -> Optional[str]:
        """Obtém o User-Agent da requisição"""
        try:
            if request:
                return request.headers.get("User-Agent", "")
        except RuntimeError:
            # Fora do contexto de requisição
            pass
        except Exception:
            pass
        return None

    @staticmethod
    def _get_session_id() -> Optional[str]:
        """Obtém o ID da sessão"""
        try:
            if session:
                return session.get("_id", "")
        except RuntimeError:
            # Fora do contexto de requisição/sessão
            pass
        except Exception:
            pass
        return None


def audit_user_changes(func):
    """Decorator para auditar alterações em usuários"""

    def wrapper(*args, **kwargs):
        # Obter instância do usuário (assumindo que é o primeiro argumento após self)
        if len(args) > 1 and hasattr(args[1], "id"):
            user = args[1]
            old_values = AuditManager._get_user_dict(user)

        result = func(*args, **kwargs)

        if len(args) > 1 and hasattr(args[1], "id"):
            user = args[1]
            new_values = AuditManager._get_user_dict(user)

            # Determinar ação baseada no método
            action = "update"
            if "create" in func.__name__.lower():
                action = "create"
            elif "delete" in func.__name__.lower():
                action = "delete"

            changed_fields = AuditManager._get_changed_fields(old_values, new_values)

            if changed_fields:
                AuditManager.log_user_change(
                    user, action, old_values, new_values, changed_fields
                )

        return result

    return wrapper


def audit_client_changes(func):
    """Decorator para auditar alterações em clientes"""

    def wrapper(*args, **kwargs):
        # Obter instância do cliente
        if len(args) > 1 and hasattr(args[1], "id"):
            client = args[1]
            old_values = AuditManager._get_client_dict(client)

        result = func(*args, **kwargs)

        if len(args) > 1 and hasattr(args[1], "id"):
            client = args[1]
            new_values = AuditManager._get_client_dict(client)

            action = "update"
            if "create" in func.__name__.lower():
                action = "create"
            elif "delete" in func.__name__.lower():
                action = "delete"

            changed_fields = AuditManager._get_changed_fields(old_values, new_values)

            if changed_fields:
                AuditManager.log_client_change(
                    client, action, old_values, new_values, changed_fields
                )

        return result

    return wrapper


# Métodos auxiliares
def _get_user_dict(user) -> Dict[str, Any]:
    """Converte usuário para dicionário"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
        "is_active": user.is_active,
        "oab_number": user.oab_number,
        "phone": user.phone,
        "cep": user.cep,
        "street": user.street,
        "city": user.city,
        "uf": user.uf,
        "specialties": user.get_specialties()
        if hasattr(user, "get_specialties")
        else None,
        "quick_actions": user.get_quick_actions()
        if hasattr(user, "get_quick_actions")
        else None,
    }


def _get_client_dict(client) -> Dict[str, Any]:
    """Converte cliente para dicionário"""
    return {
        "id": client.id,
        "full_name": client.full_name,
        "email": client.email,
        "cpf_cnpj": client.cpf_cnpj,
        "mobile_phone": client.mobile_phone,
        "cep": client.cep,
        "street": client.street,
        "city": client.city,
        "uf": client.uf,
        "profession": client.profession,
        "civil_status": client.civil_status,
    }


def _get_changed_fields(old_dict: Dict, new_dict: Dict) -> List[str]:
    """Identifica campos que foram alterados"""
    changed = []
    all_keys = set(old_dict.keys()) | set(new_dict.keys())

    for key in all_keys:
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)
        if old_val != new_val:
            changed.append(key)

    return changed
