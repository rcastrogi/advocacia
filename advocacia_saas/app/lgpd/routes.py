import json
from datetime import datetime, timezone

from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.lgpd import lgpd_bp
from app.lgpd.repository import (
    AnonymizationRequestRepository,
    ConsentRepository,
    DeanonymizationRequestRepository,
    DeletionRequestRepository,
    ProcessingLogRepository,
)
from app.models import (
    AnonymizationRequest,
    DataConsent,
    DataProcessingLog,
    DeletionRequest,
)

# =============================================================================
# PÁGINAS WEB
# =============================================================================


@lgpd_bp.route("/privacy")
@login_required
def privacy():
    """Página de privacidade e LGPD para usuários"""
    return render_template("lgpd/privacy.html")


# =============================================================================
# CONSENTIMENTO DE DADOS
# =============================================================================


@lgpd_bp.route("/consent", methods=["GET"])
@login_required
def get_user_consents():
    """Obtém consentimentos do usuário atual"""
    consents = ConsentRepository.get_by_user(current_user.id)
    return jsonify([consent.to_dict() for consent in consents])


@lgpd_bp.route("/consent", methods=["POST"])
@login_required
def give_consent():
    """Registra consentimento para tratamento de dados"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Dados não fornecidos"}), 400

    required_fields = ["consent_type", "consent_purpose"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo obrigatório: {field}"}), 400

    # Criar consentimento
    consent = ConsentRepository.create(
        {
            "user_id": current_user.id,
            "consent_type": data["consent_type"],
            "consent_purpose": data["consent_purpose"],
            "consent_version": data.get("consent_version", "1.0"),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
            "consent_method": "web_form",
        }
    )

    # Log do processamento
    log_processing(
        current_user.id,
        "consent",
        "personal",
        ["consent"],
        "User consented to data processing",
    )

    return jsonify(
        {
            "message": "Consentimento registrado com sucesso",
            "consent_id": consent.id,
        }
    ), 201


@lgpd_bp.route("/consent/<int:consent_id>", methods=["DELETE"])
@login_required
def withdraw_consent(consent_id):
    """Retira consentimento"""
    consent = DataConsent.query.filter_by(
        id=consent_id, user_id=current_user.id
    ).first()

    if not consent:
        return jsonify({"error": "Consentimento não encontrado"}), 404

    consent.withdraw_consent()

    # Log do processamento
    log_processing(
        current_user.id,
        "withdraw_consent",
        "personal",
        ["consent"],
        "User withdrew data consent",
    )

    return jsonify({"message": "Consentimento retirado com sucesso"})


# =============================================================================
# DIREITO AO ESQUECIMENTO
# =============================================================================


@lgpd_bp.route("/deletion-request", methods=["POST"])
@login_required
def request_data_deletion():
    """Solicita exclusão de dados (Direito ao Esquecimento)"""
    data = request.get_json()

    if not data or "reason" not in data:
        return jsonify({"error": "Motivo da solicitação é obrigatório"}), 400

    # Verificar se já existe uma solicitação pendente
    existing_request = DeletionRequestRepository.get_pending_by_user(current_user.id)

    if existing_request:
        return jsonify(
            {
                "error": "Já existe uma solicitação de exclusão pendente",
                "request_id": existing_request.id,
            }
        ), 409

    # Criar solicitação
    deletion_request = DeletionRequestRepository.create(
        user_id=current_user.id,
        reason=data["reason"],
        scope=data.get("scope", ["account", "data"]),
    )

    # Log do processamento
    log_processing(
        current_user.id,
        "deletion_request",
        "personal",
        ["request"],
        "User requested data deletion",
    )

    return jsonify(
        {
            "message": "Solicitação de exclusão registrada",
            "request_id": deletion_request.id,
            "status": "pending",
        }
    ), 201


@lgpd_bp.route("/deletion-request", methods=["GET"])
@login_required
def get_deletion_requests():
    """Obtém solicitações de exclusão do usuário"""
    requests = DeletionRequestRepository.get_by_user(current_user.id)
    return jsonify([req.to_dict() for req in requests])


# =============================================================================
# ANONIMIZAÇÃO
# =============================================================================


@lgpd_bp.route("/anonymization-request", methods=["POST"])
@login_required
def request_anonymization():
    """Solicita anonimização de dados"""
    data = request.get_json()

    if not data or "reason" not in data:
        return jsonify({"error": "Motivo da solicitação é obrigatório"}), 400

    # Verificar se já existe uma solicitação pendente
    existing_request = AnonymizationRequestRepository.get_pending_by_user(
        current_user.id
    )

    if existing_request:
        return jsonify(
            {
                "error": "Já existe uma solicitação de anonimização pendente",
                "request_id": existing_request.id,
            }
        ), 409

    # Criar solicitação
    anonymization_request = AnonymizationRequestRepository.create(
        user_id=current_user.id,
        reason=data["reason"],
        categories=data.get("categories", ["personal"]),
        method=data.get("method", "pseudonymization"),
    )

    # Log do processamento
    log_processing(
        current_user.id,
        "anonymization_request",
        "personal",
        ["request"],
        "User requested data anonymization",
    )

    return jsonify(
        {
            "message": "Solicitação de anonimização registrada",
            "request_id": anonymization_request.id,
            "status": "pending",
        }
    ), 201


@lgpd_bp.route("/anonymization-request", methods=["GET"])
@login_required
def get_user_anonymization_requests():
    """Obtém solicitações de anonimização do usuário"""
    requests = AnonymizationRequestRepository.get_by_user(current_user.id)
    return jsonify([req.to_dict() for req in requests])


# =============================================================================
# LOG DE PROCESSAMENTO
# =============================================================================


@lgpd_bp.route("/processing-log", methods=["GET"])
@login_required
def get_processing_log():
    """Obtém log de processamento de dados do usuário"""
    logs = ProcessingLogRepository.get_by_user(current_user.id)
    return jsonify([log.to_dict() for log in logs])


# =============================================================================
# ADMIN ENDPOINTS (Para processar solicitações)
# =============================================================================


@lgpd_bp.route("/admin/deletion-requests", methods=["GET"])
@login_required
def get_pending_deletion_requests():
    """Admin: Lista solicitações de exclusão pendentes"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    requests = DeletionRequestRepository.get_all_pending()
    return jsonify([req.to_dict() for req in requests])


@lgpd_bp.route("/admin/deletion-request/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_deletion_request(request_id):
    """Aprova uma solicitação de exclusão (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = DeletionRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes")

    try:
        # Executar exclusão dos dados do usuário via repository
        audit_data = DeletionRequestRepository.approve(
            request_obj, current_user.id, admin_notes
        )

        # Log de auditoria adicional
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "deletion_request_approved",
                "data_category": "user_account",
                "purpose": "right_to_erasure",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "audit_data": audit_data,
                    "processed_by": current_user.email,
                },
            }
        )

        return jsonify(
            {"message": "Solicitação de exclusão aprovada e dados removidos"}
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao processar exclusão: {str(e)}"}), 500


@lgpd_bp.route("/admin/deletion-request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_deletion_request(request_id):
    """Rejeita uma solicitação de exclusão (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = DeletionRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes", "")
    rejection_reason = data.get(
        "rejection_reason", "Solicitação rejeitada pelo administrador"
    )

    try:
        # Rejeitar via repository
        DeletionRequestRepository.reject(
            request_obj, current_user.id, rejection_reason, admin_notes
        )

        # Log de auditoria
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "deletion_request_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": current_user.email,
                },
            }
        )

        return jsonify({"message": "Solicitação de exclusão rejeitada"})

    except Exception as e:
        return jsonify({"error": f"Erro ao rejeitar solicitação: {str(e)}"}), 500


@lgpd_bp.route("/admin/anonymization-requests", methods=["GET"])
@login_required
def get_admin_anonymization_requests():
    """Obtém todas as solicitações de anonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    requests = AnonymizationRequestRepository.get_all()
    result = []
    for req in requests:
        data = req.to_dict()
        data["user_email"] = req.user.email if req.user else None
        data["processed_by_email"] = (
            req.processed_by.email if req.processed_by else None
        )
        result.append(data)

    return jsonify(result)


@lgpd_bp.route("/admin/consents", methods=["GET"])
@login_required
def get_all_consents():
    """Obtém todos os consentimentos (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    consents = ConsentRepository.get_all()
    result = []
    for consent in consents:
        data = consent.to_dict()
        data["user_email"] = consent.user.email if consent.user else None
        result.append(data)

    return jsonify(result)


@lgpd_bp.route("/admin/audit-log", methods=["GET"])
@login_required
def get_audit_log():
    """Obtém log de auditoria de processamento de dados (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    date_filter = request.args.get("date")
    filter_date = None

    if date_filter:
        try:
            filter_date = datetime.fromisoformat(date_filter)
        except ValueError:
            return jsonify({"error": "Formato de data inválido"}), 400

    logs = ProcessingLogRepository.get_all_filtered(date_filter=filter_date)
    result = []
    for log in logs:
        data = log.to_dict()
        data["user_email"] = log.user.email if log.user else None
        result.append(data)

    return jsonify(result)


@lgpd_bp.route("/admin/anonymization-request/<int:request_id>", methods=["GET"])
@login_required
def get_anonymization_request_details(request_id):
    """Obtém detalhes de uma solicitação de anonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = AnonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    data = request_obj.to_dict()
    data["user_email"] = request_obj.user.email if request_obj.user else None
    data["processed_by_email"] = (
        request_obj.processed_by.email if request_obj.processed_by else None
    )

    return jsonify(data)


@lgpd_bp.route(
    "/admin/anonymization-request/<int:request_id>/approve", methods=["POST"]
)
@login_required
def approve_anonymization_request(request_id):
    """Aprova uma solicitação de anonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = AnonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes")

    try:
        # Executar anonimização via repository
        AnonymizationRequestRepository.approve(
            request_obj, current_user.id, admin_notes
        )

        # Log de auditoria
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "data_anonymization",
                "data_category": request_obj.data_categories or "personal_data",
                "purpose": "data_minimization",
                "legal_basis": "LGPD Art. 12",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "processed_by": current_user.email,
                },
            }
        )

        return jsonify(
            {"message": "Solicitação de anonimização aprovada e dados anonimizados"}
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao processar anonimização: {str(e)}"}), 500


@lgpd_bp.route("/admin/anonymization-request/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_anonymization_request(request_id):
    """Rejeita uma solicitação de anonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = AnonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes", "")
    rejection_reason = data.get(
        "rejection_reason", "Solicitação rejeitada pelo administrador"
    )

    try:
        # Rejeitar via repository
        AnonymizationRequestRepository.reject(
            request_obj, current_user.id, rejection_reason, admin_notes
        )

        # Log de auditoria
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "anonymization_request_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 12",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": current_user.email,
                },
            }
        )

        return jsonify({"message": "Solicitação de anonimização rejeitada"})

    except Exception as e:
        return jsonify({"error": f"Erro ao rejeitar solicitação: {str(e)}"}), 500


# =============================================================================
# DEANONYMIZATION (Reversão de Anonimização)
# =============================================================================


@lgpd_bp.route("/deanonymize", methods=["POST"])
@login_required
def request_deanonymization():
    """Usuário anonimizado solicita reversão de anonimização"""
    if current_user.billing_status != "anonymized":
        return (
            jsonify(
                {"error": "Você não está anonimizado. Esta solicitação não se aplica."}
            ),
            400,
        )

    data = request.get_json()

    if not data or "reason" not in data:
        return jsonify({"error": "Motivo da solicitação é obrigatório"}), 400

    # Verificar se já existe uma solicitação pendente
    existing_request = DeanonymizationRequestRepository.get_pending_by_user(
        current_user.id
    )

    if existing_request:
        return (
            jsonify(
                {
                    "error": "Já existe uma solicitação de deanonimização pendente",
                    "request_id": existing_request.id,
                }
            ),
            409,
        )

    # Buscar a solicitação de anonimização original
    original_anonymization = AnonymizationRequestRepository.get_completed_by_user(
        current_user.id
    )

    if not original_anonymization:
        return (
            jsonify(
                {"error": "Não foi encontrada a solicitação de anonimização original"}
            ),
            400,
        )

    try:
        # Criar solicitação de deanonimização via repository
        deanon_request = DeanonymizationRequestRepository.create(
            user_id=current_user.id,
            anonymization_request_id=original_anonymization.id,
            reason=data.get("reason"),
        )

        # Log de processamento
        log_processing(
            current_user.id,
            "deanonymization_request",
            "personal_data",
            ["deanonymization_request"],
            "User requested data deanonymization",
        )

        return (
            jsonify(
                {
                    "message": "Solicitação de deanonimização registrada",
                    "request_id": deanon_request.id,
                    "status": "pending",
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao registrar solicitação: {str(e)}"}), 500


@lgpd_bp.route("/deanonymize", methods=["GET"])
@login_required
def get_user_deanonymization_requests():
    """Obtém solicitações de deanonimização do usuário"""
    requests = DeanonymizationRequestRepository.get_by_user(current_user.id)
    return jsonify([req.to_dict() for req in requests])


@lgpd_bp.route("/admin/deanonymization-requests", methods=["GET"])
@login_required
def get_admin_deanonymization_requests():
    """Obtém todas as solicitações de deanonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    requests = DeanonymizationRequestRepository.get_all()
    result = []
    for req in requests:
        data = req.to_dict()
        data["user_email"] = req.user.email if req.user else None
        data["processed_by_email"] = req.processor.email if req.processor else None
        result.append(data)

    return jsonify(result)


@lgpd_bp.route("/admin/deanonymization-request/<int:request_id>", methods=["GET"])
@login_required
def get_deanonymization_request_details(request_id):
    """Obtém detalhes de uma solicitação de deanonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = DeanonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    data = request_obj.to_dict()
    data["user_email"] = request_obj.user.email if request_obj.user else None
    data["processed_by_email"] = (
        request_obj.processor.email if request_obj.processor else None
    )
    data["anonymization_request_id"] = request_obj.anonymization_request_id
    data["request_reason"] = request_obj.request_reason

    return jsonify(data)


@lgpd_bp.route(
    "/admin/deanonymization-request/<int:request_id>/approve", methods=["POST"]
)
@login_required
def approve_deanonymization_request(request_id):
    """Aprova uma solicitação de deanonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = DeanonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes")

    try:
        # Obter solicitação de anonimização original
        anonymization_request = request_obj.anonymization_request
        if not anonymization_request:
            return (
                jsonify(
                    {"error": "Solicitação de anonimização original não encontrada"}
                ),
                400,
            )

        # Restaurar dados do usuário via repository
        restored_data = DeanonymizationRequestRepository.approve(
            request_obj, current_user.id, admin_notes
        )

        # Log de auditoria
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "deanonymization_approved",
                "data_category": "personal_data",
                "purpose": "data_restoration",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "admin_notes": admin_notes,
                    "processed_by": current_user.email,
                    "restored_fields": restored_data.get("restored_fields"),
                },
            }
        )

        return jsonify(
            {"message": "Solicitação de deanonimização aprovada e dados restaurados"}
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao processar deanonimização: {str(e)}"}), 500


@lgpd_bp.route(
    "/admin/deanonymization-request/<int:request_id>/reject", methods=["POST"]
)
@login_required
def reject_deanonymization_request(request_id):
    """Rejeita uma solicitação de deanonimização (apenas admin)"""
    if not current_user.is_admin():
        return jsonify({"error": "Acesso negado"}), 403

    request_obj = DeanonymizationRequestRepository.get_by_id(request_id)
    if not request_obj:
        return jsonify({"error": "Solicitação não encontrada"}), 404
    if request_obj.status != "pending":
        return jsonify({"error": "Solicitação já foi processada"}), 400

    data = request.get_json() or {}
    admin_notes = data.get("admin_notes", "")
    rejection_reason = data.get(
        "rejection_reason", "Solicitação rejeitada pelo administrador"
    )

    try:
        # Rejeitar via repository
        DeanonymizationRequestRepository.reject(
            request_obj, current_user.id, rejection_reason, admin_notes
        )

        # Log de auditoria
        ProcessingLogRepository.create(
            {
                "user_id": request_obj.user_id,
                "action": "deanonymization_rejected",
                "data_category": "request_metadata",
                "purpose": "gdpr_compliance",
                "legal_basis": "LGPD Art. 18",
                "endpoint": request.path,
                "additional_data": {
                    "request_id": request_id,
                    "rejection_reason": rejection_reason,
                    "admin_notes": admin_notes,
                    "processed_by": current_user.email,
                },
            }
        )

        return jsonify({"message": "Solicitação de deanonimização rejeitada"})

    except Exception as e:
        return jsonify({"error": f"Erro ao rejeitar solicitação: {str(e)}"}), 500


# =============================================================================
# UTILITIES
# =============================================================================


def log_processing(
    user_id, action, data_category, data_fields, purpose, legal_basis="consent"
):
    """Registra processamento de dados no log"""
    ProcessingLogRepository.log_action(
        user_id=user_id,
        action=action,
        data_category=data_category,
        data_fields=data_fields,
        purpose=purpose,
        legal_basis=legal_basis,
    )


# =============================================================================
# MODEL METHODS EXTENSIONS
# =============================================================================


# Adicionar métodos to_dict aos modelos LGPD
def data_consent_to_dict(self):
    return {
        "id": self.id,
        "consent_type": self.consent_type,
        "consent_purpose": self.consent_purpose,
        "consented": self.consented,
        "consent_version": self.consent_version,
        "consented_at": self.consented_at.isoformat() if self.consented_at else None,
        "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
        "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        "is_valid": self.is_valid(),
    }


def deletion_request_to_dict(self):
    return {
        "id": self.id,
        "status": self.status,
        "request_reason": self.request_reason,
        "deletion_scope": self.deletion_scope,
        "requested_at": self.requested_at.isoformat(),
        "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        "rejection_reason": self.rejection_reason,
    }


def anonymization_request_to_dict(self):
    return {
        "id": self.id,
        "status": self.status,
        "request_reason": self.request_reason,
        "data_categories": self.data_categories,
        "anonymization_method": self.anonymization_method,
        "requested_at": self.requested_at.isoformat(),
        "processed_at": self.processed_at.isoformat() if self.processed_at else None,
    }


def data_processing_log_to_dict(self):
    return {
        "id": self.id,
        "action": self.action,
        "data_category": self.data_category,
        "purpose": self.purpose,
        "processed_at": self.processed_at.isoformat(),
        "legal_basis": self.legal_basis,
        "endpoint": self.endpoint,
    }


# Aplicar métodos aos modelos
DataConsent.to_dict = data_consent_to_dict
DeletionRequest.to_dict = deletion_request_to_dict
AnonymizationRequest.to_dict = anonymization_request_to_dict
DataProcessingLog.to_dict = data_processing_log_to_dict


# =============================================================================
# ADMIN PAGES
# =============================================================================


@lgpd_bp.route("/admin")
@login_required
def admin_dashboard():
    """Painel de administração LGPD"""
    if not current_user.is_admin():
        return render_template("errors/403.html"), 403
    return render_template("lgpd/admin.html")
