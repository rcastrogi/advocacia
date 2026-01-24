"""
Admin Services - Camada de lógica de negócios para administração
"""

import csv
import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

# current_app removed - unused

from app import db
from app.admin.repository import (
    AICreditConfigRepository,
    AuditLogRepository,
    CouponRepository,
    DashboardMetricsRepository,
    # PetitionModelAdminRepository removed - unused
    PetitionSectionAdminRepository,
    PetitionTypeAdminRepository,
    RoadmapCategoryRepository,
    RoadmapFeedbackRepository,
    RoadmapItemRepository,
    UserAdminRepository,
    UserCreditsAdminRepository,
)
from app.models import (
    AIGeneration,
    CreditTransaction,
    Payment,
    PetitionUsage,
    User,
)
from app.utils.pagination import PaginationHelper


# =============================================================================
# USER SERVICES
# =============================================================================


class UserAdminService:
    """Serviço para gerenciamento de usuários no admin"""

    @staticmethod
    def get_users_paginated(
        search: str = "",
        status_filter: str = "all",
        user_type_filter: str = "all",
        sort_by: str = "created_at",
        sort_order: str = "desc",
        per_page: int = 20,
    ) -> dict[str, Any]:
        """Obtém usuários paginados com métricas"""
        query = UserAdminRepository.get_filtered(
            search=search,
            status_filter=status_filter,
            user_type_filter=user_type_filter,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        pagination = PaginationHelper(
            query=query,
            per_page=per_page,
            filters={
                "search": search,
                "status": status_filter,
                "user_type": user_type_filter,
                "sort": sort_by,
                "order": sort_order,
            },
        )

        # Calcular métricas em bulk
        users_with_metrics = UserAdminService._get_bulk_user_metrics(pagination.items)

        return {
            "users": users_with_metrics,
            "pagination": pagination,
        }

    @staticmethod
    def _get_bulk_user_metrics(users: list[User]) -> list[dict]:
        """Calcula métricas para lista de usuários (evita N+1)"""
        if not users:
            return []

        user_ids = [u.id for u in users]

        # Contar petições por usuário
        petition_counts = dict(
            db.session.query(PetitionUsage.user_id, db.func.count(PetitionUsage.id))
            .filter(PetitionUsage.user_id.in_(user_ids))
            .group_by(PetitionUsage.user_id)
            .all()
        )

        # Contar gerações IA por usuário
        ai_counts = dict(
            db.session.query(AIGeneration.user_id, db.func.count(AIGeneration.id))
            .filter(AIGeneration.user_id.in_(user_ids))
            .group_by(AIGeneration.user_id)
            .all()
        )

        result = []
        for user in users:
            result.append({
                "user": user,
                "petition_count": petition_counts.get(user.id, 0),
                "ai_count": ai_counts.get(user.id, 0),
            })

        return result

    @staticmethod
    def get_user_detail(user_id: int) -> dict[str, Any] | None:
        """Obtém detalhes completos de um usuário"""
        user = UserAdminRepository.get_by_id(user_id)
        if not user:
            return None

        # Histórico de petições
        petitions = (
            PetitionUsage.query.filter_by(user_id=user_id)
            .order_by(PetitionUsage.generated_at.desc())
            .limit(20)
            .all()
        )

        # Histórico de gerações IA
        ai_generations = (
            AIGeneration.query.filter_by(user_id=user_id)
            .order_by(AIGeneration.created_at.desc())
            .limit(20)
            .all()
        )

        # Histórico de transações de créditos
        credit_transactions = (
            CreditTransaction.query.filter_by(user_id=user_id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(20)
            .all()
        )

        # Histórico de pagamentos
        payments = (
            Payment.query.filter_by(user_id=user_id)
            .order_by(Payment.paid_at.desc())
            .limit(20)
            .all()
        )

        return {
            "user": user,
            "petitions": petitions,
            "ai_generations": ai_generations,
            "credit_transactions": credit_transactions,
            "payments": payments,
            "metrics": UserAdminService._get_user_metrics(user),
        }

    @staticmethod
    def _get_user_metrics(user: User) -> dict[str, Any]:
        """Calcula métricas detalhadas de um usuário"""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        return {
            "total_petitions": PetitionUsage.query.filter_by(user_id=user.id).count(),
            "month_petitions": PetitionUsage.query.filter(
                PetitionUsage.user_id == user.id,
                PetitionUsage.generated_at >= month_start,
            ).count(),
            "total_ai_generations": AIGeneration.query.filter_by(user_id=user.id).count(),
            "total_payments": Payment.query.filter_by(user_id=user.id, status="approved").count(),
        }

    @staticmethod
    def toggle_user_status(user_id: int) -> tuple[bool, str]:
        """Alterna status de usuário"""
        user = UserAdminRepository.get_by_id(user_id)
        if not user:
            return False, "Usuário não encontrado"

        if user.user_type in ["master", "admin"]:
            return False, "Não é possível desativar um administrador"

        is_active = UserAdminRepository.toggle_status(user)
        status = "ativado" if is_active else "desativado"
        return True, f"Usuário {user.username} foi {status} com sucesso"

    @staticmethod
    def add_credits(user_id: int, amount: int, reason: str) -> tuple[bool, str, int]:
        """Adiciona créditos a um usuário"""
        if amount <= 0:
            return False, "Quantidade deve ser maior que zero", 0

        user = UserAdminRepository.get_by_id(user_id)
        if not user:
            return False, "Usuário não encontrado", 0

        new_balance = UserCreditsAdminRepository.add_credits(user_id, amount, reason)
        return True, f"{amount} créditos adicionados. Novo saldo: {new_balance}", new_balance

    @staticmethod
    def export_users_csv() -> StringIO:
        """Exporta usuários para CSV"""
        users = User.query.order_by(User.created_at.desc()).all()

        output = StringIO()
        writer = csv.writer(output)

        # Cabeçalho
        writer.writerow([
            "ID", "Username", "Email", "Nome Completo", "OAB", "Tipo",
            "Status", "Billing Status", "Créditos IA", "Criado em",
        ])

        for user in users:
            writer.writerow([
                user.id,
                user.username,
                user.email,
                user.full_name or "",
                user.oab_number or "",
                user.user_type,
                "Ativo" if user.is_active else "Inativo",
                user.billing_status,
                user.ai_credits,
                user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
            ])

        output.seek(0)
        return output


# =============================================================================
# PETITION SERVICES
# =============================================================================


class PetitionTypeAdminService:
    """Serviço para tipos de petição no admin"""

    @staticmethod
    def get_all() -> list:
        """Obtém todos os tipos"""
        return PetitionTypeAdminRepository.get_all()

    @staticmethod
    def create(form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria novo tipo de petição"""
        try:
            from app.utils import generate_unique_slug

            slug = generate_unique_slug(form_data["name"], "petition_type")

            petition_type = PetitionTypeAdminRepository.create({
                "name": form_data["name"],
                "slug": slug,
                "description": form_data.get("description"),
                "category": form_data.get("category", "geral"),
                "icon": form_data.get("icon", "fas fa-file"),
                "is_active": form_data.get("is_active", True),
                "use_dynamic_form": form_data.get("use_dynamic_form", False),
            })

            return petition_type, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update(type_id: int, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza tipo de petição"""
        petition_type = PetitionTypeAdminRepository.get_by_id(type_id)
        if not petition_type:
            return False, "Tipo de petição não encontrado"

        try:
            PetitionTypeAdminRepository.update(petition_type, form_data)
            return True, "Tipo de petição atualizado com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete(type_id: int) -> tuple[bool, str]:
        """Exclui tipo de petição"""
        petition_type = PetitionTypeAdminRepository.get_by_id(type_id)
        if not petition_type:
            return False, "Tipo de petição não encontrado"

        try:
            PetitionTypeAdminRepository.delete(petition_type)
            return True, "Tipo de petição excluído com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)


class PetitionSectionAdminService:
    """Serviço para seções de petição no admin"""

    @staticmethod
    def get_all() -> list:
        """Obtém todas as seções"""
        return PetitionSectionAdminRepository.get_all()

    @staticmethod
    def get_by_id(section_id: int):
        """Obtém seção pelo ID"""
        return PetitionSectionAdminRepository.get_by_id(section_id)

    @staticmethod
    def create(form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria nova seção"""
        try:
            from app.utils import generate_unique_slug

            slug = generate_unique_slug(form_data["name"], "petition_section")

            fields_schema = form_data.get("fields_schema")
            if isinstance(fields_schema, str):
                fields_schema = json.loads(fields_schema)

            section = PetitionSectionAdminRepository.create({
                "name": form_data["name"],
                "slug": slug,
                "description": form_data.get("description"),
                "icon": form_data.get("icon", "fas fa-file-alt"),
                "color": form_data.get("color", "#6c757d"),
                "fields_schema": fields_schema or [],
                "is_active": form_data.get("is_active", True),
            })

            return section, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update(section_id: int, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza seção"""
        section = PetitionSectionAdminRepository.get_by_id(section_id)
        if not section:
            return False, "Seção não encontrada"

        try:
            fields_schema = form_data.get("fields_schema")
            if isinstance(fields_schema, str):
                fields_schema = json.loads(fields_schema)
            form_data["fields_schema"] = fields_schema

            PetitionSectionAdminRepository.update(section, form_data)
            return True, "Seção atualizada com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete(section_id: int) -> tuple[bool, str]:
        """Exclui seção"""
        section = PetitionSectionAdminRepository.get_by_id(section_id)
        if not section:
            return False, "Seção não encontrada"

        try:
            PetitionSectionAdminRepository.delete(section)
            return True, "Seção excluída com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)


# =============================================================================
# ROADMAP SERVICES
# =============================================================================


class RoadmapAdminService:
    """Serviço para gerenciamento do roadmap"""

    @staticmethod
    def get_categories() -> list:
        """Obtém todas as categorias"""
        return RoadmapCategoryRepository.get_all()

    @staticmethod
    def create_category(form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria nova categoria"""
        try:
            category = RoadmapCategoryRepository.create(form_data)
            return category, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_category(category_id: int, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza categoria"""
        category = RoadmapCategoryRepository.get_by_id(category_id)
        if not category:
            return False, "Categoria não encontrada"

        try:
            RoadmapCategoryRepository.update(category, form_data)
            return True, "Categoria atualizada com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_items(status: str | None = None, category_id: int | None = None) -> list:
        """Obtém itens do roadmap"""
        return RoadmapItemRepository.get_all(status=status, category_id=category_id)

    @staticmethod
    def create_item(form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria novo item"""
        try:
            item = RoadmapItemRepository.create(form_data)
            return item, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_item(item_id: int, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza item"""
        item = RoadmapItemRepository.get_by_id(item_id)
        if not item:
            return False, "Item não encontrado"

        try:
            RoadmapItemRepository.update(item, form_data)
            return True, "Item atualizado com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def toggle_item_visibility(item_id: int) -> tuple[bool, str]:
        """Alterna visibilidade do item"""
        item = RoadmapItemRepository.get_by_id(item_id)
        if not item:
            return False, "Item não encontrado"

        is_visible = RoadmapItemRepository.toggle_visibility(item)
        status = "visível" if is_visible else "oculto"
        return True, f"Item agora está {status}"


class RoadmapFeedbackService:
    """Serviço para feedbacks do roadmap"""

    @staticmethod
    def get_all(status: str | None = None) -> list:
        """Obtém todos os feedbacks"""
        return RoadmapFeedbackRepository.get_all(status=status)

    @staticmethod
    def respond(feedback_id: int, response: str) -> tuple[bool, str]:
        """Responde a um feedback"""
        feedback = RoadmapFeedbackRepository.get_by_id(feedback_id)
        if not feedback:
            return False, "Feedback não encontrado"

        RoadmapFeedbackRepository.add_response(feedback, response)
        return True, "Resposta enviada com sucesso"

    @staticmethod
    def update_status(feedback_id: int, status: str) -> tuple[bool, str]:
        """Atualiza status do feedback"""
        feedback = RoadmapFeedbackRepository.get_by_id(feedback_id)
        if not feedback:
            return False, "Feedback não encontrado"

        RoadmapFeedbackRepository.update_status(feedback, status)
        return True, f"Status atualizado para {status}"


# =============================================================================
# COUPON SERVICES
# =============================================================================


class CouponAdminService:
    """Serviço para cupons promocionais (PromoCoupon)"""

    @staticmethod
    def get_all() -> list:
        """Obtém todos os cupons"""
        return CouponRepository.get_all()

    @staticmethod
    def get_by_id(coupon_id: int):
        """Obtém cupom pelo ID"""
        return CouponRepository.get_by_id(coupon_id)

    @staticmethod
    def create(created_by_id: int, form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria novo cupom promocional"""
        code = form_data.get("code", "").upper().strip()

        # Verificar se código já existe (se fornecido)
        if code:
            existing = CouponRepository.get_by_code(code)
            if existing:
                return None, "Código de cupom já existe"

        try:
            expires_at = None
            if form_data.get("expires_at"):
                expires_at = datetime.strptime(form_data["expires_at"], "%Y-%m-%d")
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            coupon = CouponRepository.create(
                created_by_id=created_by_id,
                data={
                    "code": code if code else None,
                    "benefit_days": int(form_data.get("benefit_days", 0)),
                    "benefit_credits": int(form_data.get("benefit_credits", 0)),
                    "expires_at": expires_at,
                    "description": form_data.get("description"),
                },
            )

            return coupon, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def delete(coupon_id: int) -> tuple[bool, str]:
        """Exclui cupom"""
        coupon = CouponRepository.get_by_id(coupon_id)
        if not coupon:
            return False, "Cupom não encontrado"

        if coupon.is_used:
            return False, "Cupom já foi utilizado e não pode ser excluído"

        try:
            CouponRepository.delete(coupon)
            return True, "Cupom excluído com sucesso"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def validate_coupon(code: str) -> tuple[dict | None, str | None]:
        """Valida um cupom"""
        coupon = CouponRepository.get_by_code(code)

        if not coupon:
            return None, "Cupom não encontrado"

        # Usar o método is_valid do modelo
        is_valid, error_msg = coupon.is_valid()
        if not is_valid:
            return None, error_msg

        return {
            "id": coupon.id,
            "code": coupon.code,
            "benefit_days": coupon.benefit_days,
            "benefit_credits": coupon.benefit_credits,
        }, None


# =============================================================================
# AI CONFIG SERVICES
# =============================================================================


class AICreditConfigService:
    """Serviço para configurações de créditos de IA"""

    @staticmethod
    def get_all() -> list:
        """Obtém todas as configurações"""
        return AICreditConfigRepository.get_all()

    @staticmethod
    def update(config_id: int, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza configuração"""
        config = AICreditConfigRepository.get_by_id(config_id)
        if not config:
            return False, "Configuração não encontrada"

        try:
            AICreditConfigRepository.update(config, {
                "credit_cost": int(form_data.get("credit_cost", config.credit_cost)),
                "is_premium": form_data.get("is_premium", config.is_premium),
                "is_active": form_data.get("is_active", config.is_active),
            })
            return True, f"Configuração '{config.name}' atualizada"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def reset_to_defaults() -> tuple[bool, str]:
        """Reseta configurações para padrão"""
        try:
            count = AICreditConfigRepository.reset_to_defaults()
            return True, f"{count} configurações resetadas para padrão"
        except Exception as e:
            db.session.rollback()
            return False, str(e)


# =============================================================================
# AUDIT LOG SERVICES
# =============================================================================


class AuditLogService:
    """Serviço para logs de auditoria"""

    @staticmethod
    def get_paginated(
        entity_type: str | None = None,
        action: str | None = None,
        user_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """Obtém logs paginados"""
        query = AuditLogRepository.get_filtered(
            entity_type=entity_type,
            action=action,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        pagination = PaginationHelper(
            query=query,
            per_page=per_page,
            filters={
                "entity_type": entity_type,
                "action": action,
                "user_id": user_id,
            },
        )

        return {
            "logs": pagination.items,
            "pagination": pagination,
        }

    @staticmethod
    def get_by_id(log_id: int):
        """Obtém log pelo ID"""
        return AuditLogRepository.get_by_id(log_id)

    @staticmethod
    def get_entity_history(entity_type: str, entity_id: int) -> list:
        """Obtém histórico de uma entidade"""
        return AuditLogRepository.get_by_entity(entity_type, entity_id)


# =============================================================================
# DASHBOARD SERVICES
# =============================================================================


class DashboardService:
    """Serviço para métricas do dashboard"""

    @staticmethod
    def get_overview_stats() -> dict[str, Any]:
        """Obtém estatísticas gerais"""
        user_stats = UserAdminRepository.count_by_status()
        petition_stats = DashboardMetricsRepository.get_petition_stats()
        ai_stats = DashboardMetricsRepository.get_ai_stats()
        payment_stats = DashboardMetricsRepository.get_payment_stats()

        return {
            "users": user_stats,
            "petitions": petition_stats,
            "ai": ai_stats,
            "payments": payment_stats,
            "new_users_30d": UserAdminRepository.count_new_in_period(30),
            "petition_types_count": PetitionTypeAdminRepository.count(),
        }

    @staticmethod
    def get_alerts() -> list[dict]:
        """Gera alertas para métricas críticas"""
        alerts = []
        now = datetime.now(timezone.utc)

        # Alerta de usuários em trial expirando
        week_from_now = now + timedelta(days=7)
        trial_expiring = User.query.filter(
            User.billing_status == "trial",
            User.trial_ends_at.isnot(None),
            User.trial_ends_at <= week_from_now,
            User.trial_ends_at >= now,
        ).count()

        if trial_expiring > 0:
            alerts.append({
                "type": "warning",
                "icon": "fas fa-clock",
                "message": f"{trial_expiring} usuários com trial expirando nos próximos 7 dias",
            })

        # Alerta de usuários inadimplentes
        delinquent = User.query.filter(User.billing_status == "delinquent").count()
        if delinquent > 0:
            alerts.append({
                "type": "danger",
                "icon": "fas fa-exclamation-triangle",
                "message": f"{delinquent} usuários inadimplentes",
            })

        return alerts
