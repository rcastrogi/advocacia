"""
Deadlines Services - Camada de lógica de negócios
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from flask import current_app, url_for

from app import db
from app.deadlines.repository import (
    AgendaBlockRepository,
    ClientForDeadlineRepository,
    DeadlineRepository,
)
from app.models import Notification
from app.processes.automation import run_process_automations
from app.utils.email import send_email
from app.utils.pagination import PaginationHelper


class DeadlineService:
    """Serviço para gerenciamento de prazos"""

    @staticmethod
    def get_deadlines_paginated(
        user_id: int,
        status: str = "pending",
        deadline_type: str | None = None,
    ) -> dict[str, Any]:
        """Obtém prazos paginados com separação por urgência"""
        query = DeadlineRepository.get_by_user_filtered(user_id, status, deadline_type)

        pagination = PaginationHelper(
            query=query,
            per_page=20,
            filters={"status": status, "type": deadline_type},
        )

        deadlines = pagination.items

        urgent = [d for d in deadlines if d.is_urgent()]
        upcoming = [d for d in deadlines if not d.is_urgent() and d.status == "pending"]

        return {
            "urgent_deadlines": urgent,
            "upcoming_deadlines": upcoming,
            "all_deadlines": deadlines,
            "pagination": pagination.to_dict(),
        }

    @staticmethod
    def get_deadline_with_access_check(
        deadline_id: int, user_id: int
    ) -> tuple[Any, str | None]:
        """Obtém prazo verificando acesso do usuário"""
        deadline = DeadlineRepository.get_by_id(deadline_id)

        if not deadline:
            return None, "Prazo não encontrado"

        if deadline.user_id != user_id:
            return None, "Acesso negado"

        return deadline, None

    @staticmethod
    def get_form_data(user_id: int) -> dict[str, Any]:
        """Obtém dados para formulários de prazo"""
        clients = ClientForDeadlineRepository.get_by_user_ordered(user_id)
        return {"clients": clients}

    @staticmethod
    def create_deadline(
        user_id: int, form_data: dict[str, Any]
    ) -> tuple[Any, str | None]:
        """Cria um novo prazo"""
        try:
            deadline_date = datetime.strptime(
                form_data["deadline_date"], "%Y-%m-%dT%H:%M"
            )

            client_id = form_data.get("client_id")
            if client_id:
                client_id = int(client_id)

            deadline = DeadlineRepository.create(
                {
                    "user_id": user_id,
                    "title": form_data["title"],
                    "description": form_data.get("description"),
                    "deadline_type": form_data.get("deadline_type"),
                    "deadline_date": deadline_date,
                    "alert_days_before": int(form_data.get("alert_days_before", 7)),
                    "count_business_days": form_data.get("count_business_days") == "on",
                    "client_id": client_id,
                }
            )

            return deadline, None

        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao criar prazo: {str(e)}"

    @staticmethod
    def update_deadline(
        deadline_id: int, user_id: int, form_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Atualiza um prazo"""
        deadline, error = DeadlineService.get_deadline_with_access_check(
            deadline_id, user_id
        )
        if error:
            return False, error

        try:
            deadline_date = datetime.strptime(
                form_data["deadline_date"], "%Y-%m-%dT%H:%M"
            )

            DeadlineRepository.update(
                deadline,
                {
                    "title": form_data["title"],
                    "description": form_data.get("description"),
                    "deadline_type": form_data.get("deadline_type"),
                    "deadline_date": deadline_date,
                    "alert_days_before": int(form_data.get("alert_days_before", 7)),
                    "count_business_days": form_data.get("count_business_days") == "on",
                },
            )

            return True, "Prazo atualizado com sucesso!"

        except Exception as e:
            db.session.rollback()
            return False, f"Erro ao atualizar prazo: {str(e)}"

    @staticmethod
    def complete_deadline(
        deadline_id: int, user_id: int, notes: str | None = None
    ) -> tuple[bool, str]:
        """Marca prazo como cumprido"""
        deadline, error = DeadlineService.get_deadline_with_access_check(
            deadline_id, user_id
        )
        if error:
            return False, error

        DeadlineRepository.mark_completed(deadline, notes)
        return True, "Prazo marcado como cumprido"

    @staticmethod
    def delete_deadline(deadline_id: int, user_id: int) -> tuple[bool, str]:
        """Exclui um prazo"""
        deadline, error = DeadlineService.get_deadline_with_access_check(
            deadline_id, user_id
        )
        if error:
            return False, error

        DeadlineRepository.delete(deadline)
        return True, "Prazo excluído com sucesso"

    @staticmethod
    def get_upcoming_deadlines(user_id: int, days: int = 7) -> list[dict]:
        """Obtém próximos prazos para API"""
        deadlines = DeadlineRepository.get_upcoming(user_id, days)
        return [d.to_dict() for d in deadlines]


class DeadlineAlertService:
    """Serviço para alertas de prazos (cron job)"""

    @staticmethod
    def validate_api_key(api_key: str | None) -> tuple[bool, str | None]:
        """Valida API key para cron"""
        expected_key = os.environ.get("CRON_API_KEY")

        if not expected_key:
            current_app.logger.warning(
                "CRON_API_KEY não configurada - endpoint desabilitado"
            )
            return False, "Endpoint não configurado"

        if not api_key or api_key != expected_key:
            current_app.logger.warning(
                "Tentativa de acesso não autorizado ao cron de alertas"
            )
            return False, "API key inválida"

        return True, None

    @staticmethod
    def send_pending_alerts() -> int:
        """Envia alertas para prazos pendentes"""
        deadlines = DeadlineRepository.get_pending_alerts()
        alerts_sent = 0

        for deadline in deadlines:
            days_until = deadline.days_until()

            if 0 <= days_until <= deadline.alert_days_before:
                try:
                    run_process_automations(
                        user_id=deadline.user_id,
                        event_data={
                            "trigger_type": "deadline",
                            "process_id": deadline.process_id,
                            "process_title": deadline.process.title
                            if deadline.process
                            else None,
                            "days_before": int(days_until),
                            "deadline_id": deadline.id,
                            "deadline_title": deadline.title,
                        },
                    )

                    send_email(
                        to=deadline.user.email,
                        subject=f"⚠️ Prazo próximo: {deadline.title}",
                        template="emails/deadline_alert.html",
                        deadline=deadline,
                        days_until=days_until,
                    )

                    Notification.create_notification(
                        user_id=deadline.user_id,
                        notification_type="deadline",
                        title="Prazo próximo",
                        message=f"{deadline.title} vence em {days_until} dias",
                        link=url_for("deadlines.view", deadline_id=deadline.id),
                    )

                    DeadlineRepository.mark_alert_sent(deadline)
                    alerts_sent += 1

                except Exception as e:
                    current_app.logger.error(f"Erro ao enviar alerta: {str(e)}")

        db.session.commit()
        return alerts_sent


class AgendaBlockService:
    """Serviço para bloqueios de agenda"""

    @staticmethod
    def get_user_blocks(user_id: int) -> list:
        """Obtém bloqueios do usuário"""
        return AgendaBlockRepository.get_by_user(user_id)

    @staticmethod
    def get_block_with_access_check(
        block_id: int, user_id: int
    ) -> tuple[Any, str | None]:
        """Obtém bloqueio verificando acesso"""
        block = AgendaBlockRepository.get_by_id(block_id)

        if not block:
            return None, "Bloqueio não encontrado"

        if block.user_id != user_id:
            return None, "Acesso negado"

        return block, None

    @staticmethod
    def create_block(user_id: int, form_data: dict[str, Any]) -> tuple[Any, str | None]:
        """Cria um novo bloqueio de agenda"""
        try:
            weekdays = form_data.get("weekdays", [])
            weekdays_json = json.dumps([int(d) for d in weekdays]) if weekdays else None

            time_type = form_data.get("time_type", "period")
            all_day = time_type == "all_day"
            day_period = form_data.get("day_period") if time_type == "period" else None

            start_time = None
            end_time = None
            if time_type == "specific":
                start_time_str = form_data.get("start_time")
                end_time_str = form_data.get("end_time")
                if start_time_str:
                    start_time = datetime.strptime(start_time_str, "%H:%M").time()
                if end_time_str:
                    end_time = datetime.strptime(end_time_str, "%H:%M").time()

            start_date = None
            end_date = None
            start_date_str = form_data.get("start_date")
            end_date_str = form_data.get("end_date")
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            block = AgendaBlockRepository.create(
                {
                    "user_id": user_id,
                    "title": form_data["title"],
                    "description": form_data.get("description"),
                    "block_type": form_data.get("block_type", "recurring"),
                    "weekdays": weekdays_json,
                    "start_time": start_time,
                    "end_time": end_time,
                    "all_day": all_day,
                    "day_period": day_period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "color": form_data.get("color", "#6c757d"),
                }
            )

            return block, None

        except Exception as e:
            db.session.rollback()
            return None, f"Erro ao criar bloqueio: {str(e)}"

    @staticmethod
    def update_block(
        block_id: int, user_id: int, form_data: dict[str, Any]
    ) -> tuple[bool, str]:
        """Atualiza um bloqueio de agenda"""
        block, error = AgendaBlockService.get_block_with_access_check(block_id, user_id)
        if error:
            return False, error

        try:
            weekdays = form_data.get("weekdays", [])
            weekdays_json = json.dumps([int(d) for d in weekdays]) if weekdays else None

            time_type = form_data.get("time_type", "period")
            all_day = time_type == "all_day"
            day_period = form_data.get("day_period") if time_type == "period" else None

            start_time = None
            end_time = None
            if time_type == "specific":
                start_time_str = form_data.get("start_time")
                end_time_str = form_data.get("end_time")
                if start_time_str:
                    start_time = datetime.strptime(start_time_str, "%H:%M").time()
                if end_time_str:
                    end_time = datetime.strptime(end_time_str, "%H:%M").time()

            start_date = None
            end_date = None
            start_date_str = form_data.get("start_date")
            end_date_str = form_data.get("end_date")
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            AgendaBlockRepository.update(
                block,
                {
                    "title": form_data["title"],
                    "description": form_data.get("description"),
                    "block_type": form_data.get("block_type", "recurring"),
                    "weekdays": weekdays_json,
                    "start_time": start_time,
                    "end_time": end_time,
                    "all_day": all_day,
                    "day_period": day_period,
                    "start_date": start_date,
                    "end_date": end_date,
                    "color": form_data.get("color", "#6c757d"),
                },
            )

            return True, "Bloqueio atualizado com sucesso!"

        except Exception as e:
            db.session.rollback()
            return False, f"Erro ao atualizar bloqueio: {str(e)}"

    @staticmethod
    def delete_block(block_id: int, user_id: int) -> tuple[bool, str]:
        """Exclui um bloqueio"""
        block, error = AgendaBlockService.get_block_with_access_check(block_id, user_id)
        if error:
            return False, error

        AgendaBlockRepository.delete(block)
        return True, "Bloqueio excluído com sucesso"

    @staticmethod
    def toggle_block(block_id: int, user_id: int) -> tuple[bool, str, bool | None]:
        """Ativa/desativa um bloqueio"""
        block, error = AgendaBlockService.get_block_with_access_check(block_id, user_id)
        if error:
            return False, error, None

        is_active = AgendaBlockRepository.toggle_active(block)
        status = "ativado" if is_active else "desativado"
        return True, f"Bloqueio {status}", is_active

    @staticmethod
    def get_calendar_events(
        user_id: int, start_str: str | None, end_str: str | None
    ) -> list[dict]:
        """Obtém eventos de bloqueio para o calendário"""
        try:
            start_date = (
                datetime.strptime(start_str[:10], "%Y-%m-%d").date()
                if start_str
                else datetime.now(timezone.utc).date()
            )
            end_date = (
                datetime.strptime(end_str[:10], "%Y-%m-%d").date()
                if end_str
                else (datetime.now(timezone.utc) + timedelta(days=90)).date()
            )
        except (ValueError, TypeError):
            start_date = datetime.now(timezone.utc).date()
            end_date = (datetime.now(timezone.utc) + timedelta(days=90)).date()

        blocks = AgendaBlockRepository.get_active_by_user(user_id)

        events = []
        for block in blocks:
            events.extend(block.to_calendar_events(start_date, end_date))

        return events
