from datetime import datetime, timedelta, timezone

from flask import jsonify
from sqlalchemy import and_, extract, func

from app import db
from app.models import Process, SavedPetition, process_petitions


def get_process_reports(user_id, report_type, start_date=None, end_date=None):
    """Gera relatórios sobre processos baseado no tipo solicitado."""

    if not start_date:
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
    if not end_date:
        end_date = datetime.now(timezone.utc)

    if report_type == "status_distribution":
        return get_status_distribution_report(user_id, start_date, end_date)
    elif report_type == "monthly_creation":
        return get_monthly_creation_report(user_id, start_date, end_date)
    elif report_type == "court_distribution":
        return get_court_distribution_report(user_id, start_date, end_date)
    elif report_type == "deadline_analysis":
        return get_deadline_analysis_report(user_id, start_date, end_date)
    elif report_type == "petition_process_link":
        return get_petition_process_link_report(user_id, start_date, end_date)
    else:
        return {"error": "Tipo de relatório não reconhecido"}


def get_status_distribution_report(user_id, start_date, end_date):
    """Relatório de distribuição de status dos processos."""

    status_counts = (
        db.session.query(Process.status, func.count(Process.id).label("count"))
        .filter(Process.user_id == user_id, Process.created_at.between(start_date, end_date))
        .group_by(Process.status)
        .all()
    )

    total = sum(count for _, count in status_counts)

    return {
        "report_type": "status_distribution",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_processes": total,
        "distribution": [
            {
                "status": status,
                "count": count,
                "percentage": round((count / total * 100), 2) if total > 0 else 0,
                "label": Process(status=status, user_id=user_id).get_status_text(),
            }
            for status, count in status_counts
        ],
    }


def get_monthly_creation_report(user_id, start_date, end_date):
    """Relatório de criação mensal de processos."""

    monthly_data = (
        db.session.query(
            extract("year", Process.created_at).label("year"),
            extract("month", Process.created_at).label("month"),
            func.count(Process.id).label("count"),
        )
        .filter(Process.user_id == user_id, Process.created_at.between(start_date, end_date))
        .group_by(extract("year", Process.created_at), extract("month", Process.created_at))
        .order_by(extract("year", Process.created_at), extract("month", Process.created_at))
        .all()
    )

    return {
        "report_type": "monthly_creation",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "monthly_data": [
            {
                "year": int(year),
                "month": int(month),
                "month_name": _get_month_name(int(month)),
                "count": count,
            }
            for year, month, count in monthly_data
        ],
    }


def get_court_distribution_report(user_id, start_date, end_date):
    """Relatório de distribuição por tribunal."""

    court_counts = (
        db.session.query(Process.court, func.count(Process.id).label("count"))
        .filter(
            Process.user_id == user_id,
            Process.created_at.between(start_date, end_date),
            Process.court.isnot(None),
        )
        .group_by(Process.court)
        .all()
    )

    total = sum(count for _, count in court_counts)

    return {
        "report_type": "court_distribution",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_processes": total,
        "distribution": [
            {
                "court": court or "Não informado",
                "count": count,
                "percentage": round((count / total * 100), 2) if total > 0 else 0,
            }
            for court, count in court_counts
        ],
    }


def get_deadline_analysis_report(user_id, start_date, end_date):
    """Relatório de análise de prazos."""

    # Processos com prazos
    processes_with_deadlines = Process.query.filter(
        Process.user_id == user_id,
        Process.next_deadline.isnot(None),
        Process.created_at.between(start_date, end_date),
    ).all()

    # Categorizar por urgência
    today = datetime.now(timezone.utc).date()
    analysis = {
        "overdue": [],  # Vencidos
        "due_today": [],  # Vencem hoje
        "due_soon": [],  # Vencem em até 7 dias
        "upcoming": [],  # Próximos
    }

    for process in processes_with_deadlines:
        days_until = process.days_until_deadline()

        if days_until < 0:
            analysis["overdue"].append(
                {
                    "id": process.id,
                    "title": process.title,
                    "process_number": process.process_number,
                    "deadline": process.next_deadline.isoformat(),
                    "days_overdue": abs(days_until),
                }
            )
        elif days_until == 0:
            analysis["due_today"].append(
                {
                    "id": process.id,
                    "title": process.title,
                    "process_number": process.process_number,
                    "deadline": process.next_deadline.isoformat(),
                }
            )
        elif days_until <= 7:
            analysis["due_soon"].append(
                {
                    "id": process.id,
                    "title": process.title,
                    "process_number": process.process_number,
                    "deadline": process.next_deadline.isoformat(),
                    "days_until": days_until,
                }
            )
        else:
            analysis["upcoming"].append(
                {
                    "id": process.id,
                    "title": process.title,
                    "process_number": process.process_number,
                    "deadline": process.next_deadline.isoformat(),
                    "days_until": days_until,
                }
            )

    return {
        "report_type": "deadline_analysis",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "total_with_deadlines": len(processes_with_deadlines),
        "analysis": analysis,
        "summary": {
            "overdue_count": len(analysis["overdue"]),
            "due_today_count": len(analysis["due_today"]),
            "due_soon_count": len(analysis["due_soon"]),
            "upcoming_count": len(analysis["upcoming"]),
        },
    }


def get_petition_process_link_report(user_id, start_date, end_date):
    """Relatório de vinculação entre petições e processos."""

    # Petições criadas no período
    total_petitions = SavedPetition.query.filter(
        SavedPetition.user_id == user_id,
        SavedPetition.created_at.between(start_date, end_date),
    ).count()

    # Petições finalizadas no período
    completed_petitions = SavedPetition.query.filter(
        SavedPetition.user_id == user_id,
        SavedPetition.completed_at.between(start_date, end_date),
        SavedPetition.status == "completed",
    ).count()

    # Petições com número de processo
    petitions_with_number = SavedPetition.query.filter(
        SavedPetition.user_id == user_id,
        SavedPetition.created_at.between(start_date, end_date),
        SavedPetition.process_number.isnot(None),
        SavedPetition.process_number != "",
    ).count()

    # Petições vinculadas a processos
    linked_petitions = (
        db.session.query(func.count(func.distinct(process_petitions.c.petition_id)))
        .select_from(process_petitions)
        .join(SavedPetition, process_petitions.c.petition_id == SavedPetition.id)
        .filter(
            SavedPetition.user_id == user_id,
            SavedPetition.created_at.between(start_date, end_date),
        )
        .scalar()
    )

    return {
        "report_type": "petition_process_link",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "metrics": {
            "total_petitions": total_petitions,
            "completed_petitions": completed_petitions,
            "petitions_with_number": petitions_with_number,
            "linked_petitions": linked_petitions,
            "completion_rate": (
                round((completed_petitions / total_petitions * 100), 2)
                if total_petitions > 0
                else 0
            ),
            "number_assignment_rate": (
                round((petitions_with_number / completed_petitions * 100), 2)
                if completed_petitions > 0
                else 0
            ),
            "linking_rate": (
                round((linked_petitions / completed_petitions * 100), 2)
                if completed_petitions > 0
                else 0
            ),
        },
    }


def get_dashboard_analytics(user_id):
    """Retorna dados analíticos para o dashboard."""

    # Últimos 30 dias
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Métricas básicas
    total_processes = Process.query.filter_by(user_id=user_id).count()
    active_processes = Process.query.filter_by(user_id=user_id, status="ongoing").count()
    recent_processes = Process.query.filter(
        Process.user_id == user_id, Process.created_at >= thirty_days_ago
    ).count()

    # Prazos próximos
    today = datetime.now(timezone.utc).date()
    week_from_now = today + timedelta(days=7)

    urgent_deadlines = Process.query.filter(
        Process.user_id == user_id,
        Process.next_deadline.isnot(None),
        Process.next_deadline <= week_from_now,
    ).count()

    overdue_deadlines = Process.query.filter(
        Process.user_id == user_id,
        Process.next_deadline.isnot(None),
        Process.next_deadline < today,
    ).count()

    # Distribuição por status
    status_distribution = (
        db.session.query(Process.status, func.count(Process.id).label("count"))
        .filter_by(user_id=user_id)
        .group_by(Process.status)
        .all()
    )

    return {
        "total_processes": total_processes,
        "active_processes": active_processes,
        "recent_processes": recent_processes,
        "urgent_deadlines": urgent_deadlines,
        "overdue_deadlines": overdue_deadlines,
        "status_distribution": dict(status_distribution),
    }


def _get_month_name(month_number):
    """Retorna o nome do mês em português."""
    months = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    return months.get(month_number, "")
