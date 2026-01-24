"""
LGPD Services - Camada de lógica de negócios
"""

# json removed - unused
from datetime import datetime
from typing import Any

from flask import request

from app.lgpd.repository import (
    AnonymizationRequestRepository,
    ConsentRepository,
    DeanonymizationRequestRepository,
    DeletionRequestRepository,
    ProcessingLogRepository,
)


class ConsentService:
    """Serviço para gerenciamento de consentimentos"""

    @staticmethod
    def get_user_consents(user_id: int) -> list[dict]:
        consents = ConsentRepository.get_by_user(user_id)
        return [consent.to_dict() for consent in consents]

    @staticmethod
    def create_consent(user_id: int, data: dict[str, Any]) -> tuple[dict, int]:
        """Cria um novo consentimento"""
        required_fields = ["consent_type", "consent_purpose"]
        for field in required_fields:
            if field not in data:
                return {"error": f"Campo obrigatório: {field}"}, 400

        consent = ConsentRepository.create({
            "user_id": user_id,
            "consent_type": data["consent_type"],
            "consent_purpose": data["consent_purpose"],
            "consent_version": data.get("consent_version", "1.0"),
            "ip_address": request.remote_addr if request else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
            "consent_method": "web_form",
        })

        ProcessingLogRepository.log_action(
            user_id=user_id,
            action="consent",
            data_category="personal",
            data_fields=["consent"],
            purpose="User consented to data processing",
        )

        return {
            "message": "Consentimento registrado com sucesso",
            "consent_id": consent.id,
        }, 201

    @staticmethod
    def withdraw_consent(consent_id: int, user_id: int) -> tuple[dict, int]:
        """Retira um consentimento"""
        consent = ConsentRepository.get_by_id(consent_id, user_id)

        if not consent:
            return {"error": "Consentimento não encontrado"}, 404

        ConsentRepository.withdraw(consent)

        ProcessingLogRepository.log_action(
            user_id=user_id,
            action="withdraw_consent",
            data_category="personal",
            data_fields=["consent"],
            purpose="User withdrew data consent",
        )

        return {"message": "Consentimento retirado com sucesso"}, 200


class DeletionRequestService:
    """Serviço para solicitações de exclusão (Direito ao Esquecimento)"""

    @staticmethod
    def get_user_requests(user_id: int) -> list[dict]:
        requests = DeletionRequestRepository.get_by_user(user_id)
        return [req.to_dict() for req in requests]

    @staticmethod
    def create_request(user_id: int, data: dict[str, Any]) -> tuple[dict, int]:
        """Cria uma solicitação de exclusão"""
        if not data or "reason" not in data:
            return {"error": "Motivo da solicitação é obrigatório"}, 400

        existing = DeletionRequestRepository.get_pending_by_user(user_id)
        if existing:
            return {
                "error": "Já existe uma solicitação de exclusão pendente",
                "request_id": existing.id,
            }, 409

        deletion_request = DeletionRequestRepository.create(
            user_id=user_id,
            reason=data["reason"],
            scope=data.get("scope"),
        )

        ProcessingLogRepository.log_action(
            user_id=user_id,
            action="deletion_request",
            data_category="personal",
            data_fields=["request"],
            purpose="User requested data deletion",
        )

        return {
            "message": "Solicitação de exclusão registrada",
            "request_id": deletion_request.id,
            "status": "pending",
        }, 201


class DeletionRequestAdminService:
    """Serviço admin para solicitações de exclusão"""

    @staticmethod
    def get_pending_requests() -> list[dict]:
        requests = DeletionRequestRepository.get_all_pending()
        return [req.to_dict() for req in requests]

    @staticmethod
    def approve_request(
        request_id: int, admin_id: int, admin_email: str, admin_notes: str | None = None
    ) -> tuple[dict, int]:
        """Aprova uma solicitação de exclusão"""
        deletion_request = DeletionRequestRepository.get_by_id(request_id)
        if not deletion_request:
            return {"error": "Solicitação não encontrada"}, 404

        if deletion_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        try:
            audit_data = DeletionRequestRepository.approve(
                deletion_request, admin_id, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": deletion_request.user_id,
                "action": "deletion_request_approved",
                "data_category": "user_account",
                "purpose": "right_to_erasure",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "audit_data": audit_data,
                    "processed_by": admin_email,
                },
            })

            return {"message": "Solicitação de exclusão aprovada e dados removidos"}, 200

        except Exception as e:
            return {"error": f"Erro ao processar exclusão: {str(e)}"}, 500

    @staticmethod
    def reject_request(
        request_id: int,
        admin_id: int,
        admin_email: str,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> tuple[dict, int]:
        """Rejeita uma solicitação de exclusão"""
        deletion_request = DeletionRequestRepository.get_by_id(request_id)
        if not deletion_request:
            return {"error": "Solicitação não encontrada"}, 404

        if deletion_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        try:
            DeletionRequestRepository.reject(
                deletion_request, admin_id, rejection_reason, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": deletion_request.user_id,
                "action": "deletion_request_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": admin_email,
                },
            })

            return {"message": "Solicitação de exclusão rejeitada"}, 200

        except Exception as e:
            return {"error": f"Erro ao rejeitar solicitação: {str(e)}"}, 500


class AnonymizationService:
    """Serviço para anonimização de dados"""

    @staticmethod
    def get_user_requests(user_id: int) -> list[dict]:
        requests = AnonymizationRequestRepository.get_by_user(user_id)
        return [req.to_dict() for req in requests]

    @staticmethod
    def create_request(user_id: int, data: dict[str, Any]) -> tuple[dict, int]:
        """Cria uma solicitação de anonimização"""
        if not data or "reason" not in data:
            return {"error": "Motivo da solicitação é obrigatório"}, 400

        existing = AnonymizationRequestRepository.get_pending_by_user(user_id)
        if existing:
            return {
                "error": "Já existe uma solicitação de anonimização pendente",
                "request_id": existing.id,
            }, 409

        anonymization_request = AnonymizationRequestRepository.create(
            user_id=user_id,
            reason=data["reason"],
            categories=data.get("categories"),
            method=data.get("method", "pseudonymization"),
        )

        ProcessingLogRepository.log_action(
            user_id=user_id,
            action="anonymization_request",
            data_category="personal",
            data_fields=["request"],
            purpose="User requested data anonymization",
        )

        return {
            "message": "Solicitação de anonimização registrada",
            "request_id": anonymization_request.id,
            "status": "pending",
        }, 201


class AnonymizationAdminService:
    """Serviço admin para anonimização"""

    @staticmethod
    def get_all_requests() -> list[dict]:
        requests = AnonymizationRequestRepository.get_all()
        result = []
        for req in requests:
            data = req.to_dict()
            data["user_email"] = req.user.email if req.user else None
            data["processed_by_email"] = req.processed_by.email if req.processed_by else None
            result.append(data)
        return result

    @staticmethod
    def get_request_details(request_id: int) -> tuple[dict, int]:
        request_obj = AnonymizationRequestRepository.get_by_id(request_id)
        if not request_obj:
            return {"error": "Solicitação não encontrada"}, 404

        data = request_obj.to_dict()
        data["user_email"] = request_obj.user.email if request_obj.user else None
        data["processed_by_email"] = request_obj.processed_by.email if request_obj.processed_by else None
        return data, 200

    @staticmethod
    def approve_request(
        request_id: int, admin_id: int, admin_email: str, admin_notes: str | None = None
    ) -> tuple[dict, int]:
        """Aprova uma solicitação de anonimização"""
        anonymization_request = AnonymizationRequestRepository.get_by_id(request_id)
        if not anonymization_request:
            return {"error": "Solicitação não encontrada"}, 404

        if anonymization_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        try:
            AnonymizationRequestRepository.approve(
                anonymization_request, admin_id, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": anonymization_request.user_id,
                "action": "data_anonymization",
                "data_category": anonymization_request.data_categories or "personal_data",
                "purpose": "data_minimization",
                "legal_basis": "LGPD Art. 12",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "processed_by": admin_email,
                },
            })

            return {"message": "Solicitação de anonimização aprovada e dados anonimizados"}, 200

        except Exception as e:
            return {"error": f"Erro ao processar anonimização: {str(e)}"}, 500

    @staticmethod
    def reject_request(
        request_id: int,
        admin_id: int,
        admin_email: str,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> tuple[dict, int]:
        """Rejeita uma solicitação de anonimização"""
        anonymization_request = AnonymizationRequestRepository.get_by_id(request_id)
        if not anonymization_request:
            return {"error": "Solicitação não encontrada"}, 404

        if anonymization_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        try:
            AnonymizationRequestRepository.reject(
                anonymization_request, admin_id, rejection_reason, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": anonymization_request.user_id,
                "action": "anonymization_request_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 12",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": admin_email,
                },
            })

            return {"message": "Solicitação de anonimização rejeitada"}, 200

        except Exception as e:
            return {"error": f"Erro ao rejeitar solicitação: {str(e)}"}, 500


class DeanonymizationService:
    """Serviço para deanonimização (reversão)"""

    @staticmethod
    def get_user_requests(user_id: int) -> list[dict]:
        requests = DeanonymizationRequestRepository.get_by_user(user_id)
        return [req.to_dict() for req in requests]

    @staticmethod
    def create_request(user, data: dict[str, Any]) -> tuple[dict, int]:
        """Cria uma solicitação de deanonimização"""
        if user.billing_status != "anonymized":
            return {
                "error": "Você não está anonimizado. Esta solicitação não se aplica."
            }, 400

        if not data or "reason" not in data:
            return {"error": "Motivo da solicitação é obrigatório"}, 400

        existing = DeanonymizationRequestRepository.get_pending_by_user(user.id)
        if existing:
            return {
                "error": "Já existe uma solicitação de deanonimização pendente",
                "request_id": existing.id,
            }, 409

        original_anonymization = AnonymizationRequestRepository.get_completed_by_user(user.id)
        if not original_anonymization:
            return {
                "error": "Não foi encontrada a solicitação de anonimização original"
            }, 400

        try:
            deanon_request = DeanonymizationRequestRepository.create(
                user_id=user.id,
                anonymization_request_id=original_anonymization.id,
                reason=data.get("reason"),
            )

            ProcessingLogRepository.log_action(
                user_id=user.id,
                action="deanonymization_request",
                data_category="personal_data",
                data_fields=["deanonymization_request"],
                purpose="User requested data deanonymization",
            )

            return {
                "message": "Solicitação de deanonimização registrada",
                "request_id": deanon_request.id,
                "status": "pending",
            }, 201

        except Exception as e:
            return {"error": f"Erro ao registrar solicitação: {str(e)}"}, 500


class DeanonymizationAdminService:
    """Serviço admin para deanonimização"""

    @staticmethod
    def get_all_requests() -> list[dict]:
        requests = DeanonymizationRequestRepository.get_all()
        result = []
        for req in requests:
            data = req.to_dict()
            data["user_email"] = req.user.email if req.user else None
            data["processed_by_email"] = req.processor.email if req.processor else None
            result.append(data)
        return result

    @staticmethod
    def get_request_details(request_id: int) -> tuple[dict, int]:
        request_obj = DeanonymizationRequestRepository.get_by_id(request_id)
        if not request_obj:
            return {"error": "Solicitação não encontrada"}, 404

        data = request_obj.to_dict()
        data["user_email"] = request_obj.user.email if request_obj.user else None
        data["processed_by_email"] = request_obj.processor.email if request_obj.processor else None
        data["anonymization_request_id"] = request_obj.anonymization_request_id
        data["request_reason"] = request_obj.request_reason
        return data, 200

    @staticmethod
    def approve_request(
        request_id: int, admin_id: int, admin_email: str, admin_notes: str | None = None
    ) -> tuple[dict, int]:
        """Aprova uma solicitação de deanonimização"""
        deanon_request = DeanonymizationRequestRepository.get_by_id(request_id)
        if not deanon_request:
            return {"error": "Solicitação não encontrada"}, 404

        if deanon_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        if not deanon_request.anonymization_request:
            return {"error": "Solicitação de anonimização original não encontrada"}, 400

        try:
            restored_data = DeanonymizationRequestRepository.approve(
                deanon_request, admin_id, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": deanon_request.user_id,
                "action": "deanonymization_approved",
                "data_category": "personal_data",
                "purpose": "data_restoration",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "processed_by": admin_email,
                    "restored_fields": restored_data.get("restored_fields"),
                },
            })

            return {"message": "Solicitação de deanonimização aprovada e dados restaurados"}, 200

        except Exception as e:
            return {"error": f"Erro ao processar deanonimização: {str(e)}"}, 500

    @staticmethod
    def reject_request(
        request_id: int,
        admin_id: int,
        admin_email: str,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> tuple[dict, int]:
        """Rejeita uma solicitação de deanonimização"""
        deanon_request = DeanonymizationRequestRepository.get_by_id(request_id)
        if not deanon_request:
            return {"error": "Solicitação não encontrada"}, 404

        if deanon_request.status != "pending":
            return {"error": "Solicitação já foi processada"}, 400

        try:
            DeanonymizationRequestRepository.reject(
                deanon_request, admin_id, rejection_reason, admin_notes
            )

            ProcessingLogRepository.create({
                "user_id": deanon_request.user_id,
                "action": "deanonymization_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path if request else None,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": admin_email,
                },
            })

            return {"message": "Solicitação de deanonimização rejeitada"}, 200

        except Exception as e:
            return {"error": f"Erro ao rejeitar solicitação: {str(e)}"}, 500


class ProcessingLogService:
    """Serviço para logs de processamento"""

    @staticmethod
    def get_user_logs(user_id: int) -> list[dict]:
        logs = ProcessingLogRepository.get_by_user(user_id)
        return [log.to_dict() for log in logs]

    @staticmethod
    def get_all_logs(date_filter: str | None = None) -> tuple[list[dict], int]:
        """Obtém todos os logs de auditoria (admin)"""
        filter_date = None
        if date_filter:
            try:
                filter_date = datetime.fromisoformat(date_filter)
            except ValueError:
                return {"error": "Formato de data inválido"}, 400

        logs = ProcessingLogRepository.get_all_filtered(filter_date)
        result = []
        for log in logs:
            data = log.to_dict()
            data["user_email"] = log.user.email if log.user else None
            result.append(data)

        return result, 200


class AdminConsentService:
    """Serviço admin para consentimentos"""

    @staticmethod
    def get_all_consents() -> list[dict]:
        consents = ConsentRepository.get_all()
        result = []
        for consent in consents:
            data = consent.to_dict()
            data["user_email"] = consent.user.email if consent.user else None
            result.append(data)
        return result
