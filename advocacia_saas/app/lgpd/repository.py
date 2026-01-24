"""
LGPD Repository - Camada de acesso a dados
"""

import json
from datetime import datetime, timezone
from typing import Any

from flask import request

from app import db
from app.models import (
    AnonymizationRequest,
    DataConsent,
    DataProcessingLog,
    DeanonymizationRequest,
    DeletionRequest,
)


class ConsentRepository:
    """Repositório para consentimentos de dados"""

    @staticmethod
    def get_by_user(user_id: int) -> list[DataConsent]:
        return DataConsent.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_by_id(consent_id: int, user_id: int) -> DataConsent | None:
        return DataConsent.query.filter_by(id=consent_id, user_id=user_id).first()

    @staticmethod
    def get_all() -> list[DataConsent]:
        return DataConsent.query.all()

    @staticmethod
    def create(data: dict[str, Any]) -> DataConsent:
        consent = DataConsent(
            user_id=data["user_id"],
            consent_type=data["consent_type"],
            consent_purpose=data["consent_purpose"],
            consent_version=data.get("consent_version", "1.0"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            consent_method=data.get("consent_method", "web_form"),
        )
        db.session.add(consent)
        db.session.commit()
        return consent

    @staticmethod
    def withdraw(consent: DataConsent) -> None:
        consent.withdraw_consent()


class DeletionRequestRepository:
    """Repositório para solicitações de exclusão"""

    @staticmethod
    def get_by_user(user_id: int) -> list[DeletionRequest]:
        return DeletionRequest.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_pending_by_user(user_id: int) -> DeletionRequest | None:
        return DeletionRequest.query.filter_by(
            user_id=user_id, status="pending"
        ).first()

    @staticmethod
    def get_all_pending() -> list[DeletionRequest]:
        return DeletionRequest.query.filter_by(status="pending").all()

    @staticmethod
    def get_by_id(request_id: int) -> DeletionRequest | None:
        return DeletionRequest.query.get(request_id)

    @staticmethod
    def create(user_id: int, reason: str, scope: list[str] | None = None) -> DeletionRequest:
        deletion_request = DeletionRequest(
            user_id=user_id,
            request_reason=reason,
            deletion_scope=json.dumps(scope or ["account", "data"]),
        )
        db.session.add(deletion_request)
        db.session.commit()
        return deletion_request

    @staticmethod
    def approve(
        deletion_request: DeletionRequest,
        processed_by_id: int,
        admin_notes: str | None = None,
    ) -> dict[str, Any]:
        """Aprova e executa a exclusão de dados"""
        audit_data = deletion_request.user.delete_user_data()

        deletion_request.status = "completed"
        deletion_request.processed_at = datetime.now(timezone.utc)
        deletion_request.processed_by_id = processed_by_id
        deletion_request.admin_notes = admin_notes

        db.session.commit()
        return audit_data

    @staticmethod
    def reject(
        deletion_request: DeletionRequest,
        processed_by_id: int,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> None:
        deletion_request.status = "rejected"
        deletion_request.processed_at = datetime.now(timezone.utc)
        deletion_request.processed_by_id = processed_by_id
        deletion_request.admin_notes = admin_notes
        deletion_request.rejection_reason = rejection_reason
        db.session.commit()


class AnonymizationRequestRepository:
    """Repositório para solicitações de anonimização"""

    @staticmethod
    def get_by_user(user_id: int) -> list[AnonymizationRequest]:
        return AnonymizationRequest.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_pending_by_user(user_id: int) -> AnonymizationRequest | None:
        return AnonymizationRequest.query.filter_by(
            user_id=user_id, status="pending"
        ).first()

    @staticmethod
    def get_completed_by_user(user_id: int) -> AnonymizationRequest | None:
        return AnonymizationRequest.query.filter_by(
            user_id=user_id, status="completed"
        ).first()

    @staticmethod
    def get_all() -> list[AnonymizationRequest]:
        return AnonymizationRequest.query.all()

    @staticmethod
    def get_by_id(request_id: int) -> AnonymizationRequest | None:
        return AnonymizationRequest.query.get(request_id)

    @staticmethod
    def create(
        user_id: int,
        reason: str,
        categories: list[str] | None = None,
        method: str = "pseudonymization",
    ) -> AnonymizationRequest:
        anonymization_request = AnonymizationRequest(
            user_id=user_id,
            request_reason=reason,
            data_categories=json.dumps(categories or ["personal"]),
            anonymization_method=method,
        )
        db.session.add(anonymization_request)
        db.session.commit()
        return anonymization_request

    @staticmethod
    def approve(
        anonymization_request: AnonymizationRequest,
        processed_by_id: int,
        admin_notes: str | None = None,
    ) -> dict[str, Any]:
        """Aprova e executa a anonimização"""
        result = anonymization_request.user.anonymize_personal_data()

        anonymization_request.status = "completed"
        anonymization_request.processed_at = datetime.now(timezone.utc)
        anonymization_request.processed_by_id = processed_by_id
        anonymization_request.admin_notes = admin_notes
        anonymization_request.anonymized_data = json.dumps(result)

        db.session.commit()
        return result

    @staticmethod
    def reject(
        anonymization_request: AnonymizationRequest,
        processed_by_id: int,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> None:
        anonymization_request.status = "failed"
        anonymization_request.processed_at = datetime.now(timezone.utc)
        anonymization_request.processed_by_id = processed_by_id
        anonymization_request.admin_notes = admin_notes
        anonymization_request.failure_reason = rejection_reason
        db.session.commit()


class DeanonymizationRequestRepository:
    """Repositório para solicitações de deanonimização"""

    @staticmethod
    def get_by_user(user_id: int) -> list[DeanonymizationRequest]:
        return DeanonymizationRequest.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_pending_by_user(user_id: int) -> DeanonymizationRequest | None:
        return DeanonymizationRequest.query.filter_by(
            user_id=user_id, status="pending"
        ).first()

    @staticmethod
    def get_all() -> list[DeanonymizationRequest]:
        return DeanonymizationRequest.query.all()

    @staticmethod
    def get_by_id(request_id: int) -> DeanonymizationRequest | None:
        return DeanonymizationRequest.query.get(request_id)

    @staticmethod
    def create(
        user_id: int,
        anonymization_request_id: int,
        reason: str,
    ) -> DeanonymizationRequest:
        deanon_request = DeanonymizationRequest(
            user_id=user_id,
            anonymization_request_id=anonymization_request_id,
            request_reason=reason,
        )
        db.session.add(deanon_request)
        db.session.commit()
        return deanon_request

    @staticmethod
    def approve(
        deanon_request: DeanonymizationRequest,
        processed_by_id: int,
        admin_notes: str | None = None,
    ) -> dict[str, Any]:
        """Aprova e executa a deanonimização"""
        anonymization_request = deanon_request.anonymization_request
        restored_data = deanon_request.user.restore_from_anonymization(
            anonymization_request
        )

        deanon_request.status = "approved"
        deanon_request.processed_at = datetime.now(timezone.utc)
        deanon_request.processed_by_id = processed_by_id
        deanon_request.admin_notes = admin_notes
        deanon_request.restored_data = json.dumps(restored_data)

        db.session.commit()
        return restored_data

    @staticmethod
    def reject(
        deanon_request: DeanonymizationRequest,
        processed_by_id: int,
        rejection_reason: str,
        admin_notes: str | None = None,
    ) -> None:
        deanon_request.status = "rejected"
        deanon_request.processed_at = datetime.now(timezone.utc)
        deanon_request.processed_by_id = processed_by_id
        deanon_request.admin_notes = admin_notes
        deanon_request.rejection_reason = rejection_reason
        db.session.commit()


class ProcessingLogRepository:
    """Repositório para logs de processamento"""

    @staticmethod
    def get_by_user(user_id: int, limit: int = 100) -> list[DataProcessingLog]:
        return (
            DataProcessingLog.query.filter_by(user_id=user_id)
            .order_by(DataProcessingLog.processed_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_all_filtered(
        date_filter: datetime | None = None, limit: int = 1000
    ) -> list[DataProcessingLog]:
        query = DataProcessingLog.query

        if date_filter:
            query = query.filter(
                db.func.date(DataProcessingLog.processed_at) == date_filter.date()
            )

        return query.order_by(DataProcessingLog.processed_at.desc()).limit(limit).all()

    @staticmethod
    def create(data: dict[str, Any]) -> DataProcessingLog:
        log_entry = DataProcessingLog(
            user_id=data["user_id"],
            action=data["action"],
            data_category=data["data_category"],
            data_fields=json.dumps(data.get("data_fields", [])),
            purpose=data["purpose"],
            legal_basis=data.get("legal_basis", "consent"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            endpoint=data.get("endpoint"),
            additional_data=json.dumps(data.get("additional_data", {})) if data.get("additional_data") else None,
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    @staticmethod
    def log_action(
        user_id: int,
        action: str,
        data_category: str,
        data_fields: list[str],
        purpose: str,
        legal_basis: str = "consent",
    ) -> DataProcessingLog:
        """Registra uma ação de processamento de dados"""
        return ProcessingLogRepository.create({
            "user_id": user_id,
            "action": action,
            "data_category": data_category,
            "data_fields": data_fields,
            "purpose": purpose,
            "legal_basis": legal_basis,
            "ip_address": request.remote_addr if request else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
            "endpoint": request.path if request else None,
        })
