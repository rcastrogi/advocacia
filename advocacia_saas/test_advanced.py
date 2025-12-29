#!/usr/bin/env python3
"""
Teste rápido das funcionalidades avançadas
"""

from app import create_app
from app.models import CalendarEvent, ProcessAutomation, ProcessReport

app = create_app()

with app.app_context():
    print("🧪 Testando modelos avançados...")

    # Testar CalendarEvent
    event = CalendarEvent.query.first()
    print(f"✓ CalendarEvent: {event.title if event else 'Nenhum evento encontrado'}")

    # Testar ProcessAutomation
    automation = ProcessAutomation.query.first()
    print(
        f"✓ ProcessAutomation: {automation.name if automation else 'Nenhuma automação encontrada'}"
    )

    # Testar ProcessReport
    report = ProcessReport.query.first()
    print(
        f"✓ ProcessReport: {report.title if report else 'Nenhum relatório encontrado'}"
    )

    print("✅ Todos os modelos avançados estão funcionando!")
