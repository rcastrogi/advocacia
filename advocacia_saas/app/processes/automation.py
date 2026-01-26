"""Process automation execution helpers."""

from __future__ import annotations

from typing import Any, Dict

from app.models import ProcessAutomation


def run_process_automations(user_id: int, event_data: Dict[str, Any]) -> int:
    """Executa automações ativas para o usuário com base no evento.

    Args:
        user_id: ID do usuário dono das automações.
        event_data: Dados do evento (trigger_type, process_id, etc.).

    Returns:
        Quantidade de automações executadas com sucesso.
    """
    automations = ProcessAutomation.query.filter_by(
        user_id=user_id, is_active=True
    ).all()

    executed = 0
    for automation in automations:
        try:
            if automation.should_trigger(event_data):
                if automation.execute_action(event_data):
                    executed += 1
        except Exception:
            # Evitar quebrar o fluxo principal por falha em automação
            continue

    return executed
