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
        except:
            pass
        return None

    @staticmethod
    def _get_user_agent() -> Optional[str]:
        """Obtém o User-Agent da requisição"""
        try:
            if request:
                return request.headers.get("User-Agent", "")
        except:
            pass
        return None

    @staticmethod
    def _get_session_id() -> Optional[str]:
        """Obtém o ID da sessão"""
        try:
            if session:
                return session.get("_id", "")
        except:
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
