"""
API endpoints para notificações em tempo real
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from app import db, limiter
from app.models import Notification
from app.rate_limits import AUTH_API_LIMIT

notifications_api_bp = Blueprint(
    "notifications_api", __name__, url_prefix="/api/notifications"
)


@notifications_api_bp.route("/unread-count", methods=["GET"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def get_unread_count():
    """Retorna contagem de notificações não lidas"""
    count = Notification.query.filter_by(user_id=current_user.id, read=False).count()

    return jsonify({"success": True, "count": int(count)})


@notifications_api_bp.route("/recent", methods=["GET"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def get_recent_notifications():
    """Retorna as 10 notificações mais recentes"""
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(10)
        .all()
    )

    items = []
    for notif in notifications:
        items.append(
            {
                "id": notif.id,
                "type": notif.type,
                "title": notif.title,
                "message": notif.message,
                "read": notif.read,
                "created_at": notif.created_at.isoformat()
                if notif.created_at
                else None,
                "icon": get_notification_icon(notif.type),
                "color": get_notification_color(notif.type),
                "url": notif.action_url,
            }
        )

    return jsonify(
        {
            "success": True,
            "notifications": items,
            "unread_count": int(sum(1 for n in notifications if not n.read)),
        }
    )


@notifications_api_bp.route("/<int:notification_id>/mark-read", methods=["POST"])
@login_required
@limiter.limit(AUTH_API_LIMIT)
def mark_as_read(notification_id):
    """Marca notificação como lida"""
    notification = Notification.query.filter_by(
        id=notification_id, user_id=current_user.id
    ).first()

    if not notification:
        return jsonify({"success": False, "message": "Notificação não encontrada"}), 404

    if not notification.read:
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()

    # Retornar nova contagem
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, read=False
    ).count()

    return jsonify(
        {
            "success": True,
            "message": "Notificação marcada como lida",
            "unread_count": int(unread_count),
        }
    )


@notifications_api_bp.route("/mark-all-read", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def mark_all_as_read():
    """Marca todas como lidas"""
    notifications = Notification.query.filter_by(
        user_id=current_user.id, read=False
    ).all()

    for notif in notifications:
        notif.read = True
        notif.read_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"{len(notifications)} notificações marcadas como lidas",
            "unread_count": 0,
        }
    )


def get_notification_icon(notif_type):
    """Retorna ícone FontAwesome baseado no tipo"""
    icons = {
        "info": "fa-info-circle",
        "success": "fa-check-circle",
        "warning": "fa-exclamation-triangle",
        "error": "fa-times-circle",
        "deadline": "fa-calendar-exclamation",
        "payment": "fa-credit-card",
        "process": "fa-gavel",
        "message": "fa-envelope",
        "system": "fa-cog",
    }
    return icons.get(notif_type, "fa-bell")


def get_notification_color(notif_type):
    """Retorna cor baseada no tipo"""
    colors = {
        "info": "primary",
        "success": "success",
        "warning": "warning",
        "error": "danger",
        "deadline": "danger",
        "payment": "success",
        "process": "info",
        "message": "primary",
        "system": "secondary",
    }
    return colors.get(notif_type, "secondary")
