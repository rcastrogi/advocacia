from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user

from app import db
from app.billing.utils import ensure_default_plan
from app.models import UserPlan


def subscription_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        ensure_default_plan()
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        plan = current_user.get_active_plan()
        if not plan:
            default_plan = ensure_default_plan()
            plan = UserPlan(user_id=current_user.id, plan_id=default_plan.id)
            db.session.add(plan)
            db.session.commit()

        if (
            not plan
            or plan.status != "active"
            or current_user.is_delinquent
            or current_user.is_trial_expired
        ):
            if current_user.is_trial_expired:
                flash(
                    "Seu período de teste expirou. Assine um plano para continuar usando o sistema.",
                    "warning",
                )
            else:
                flash(
                    "Sua assinatura está inativa ou em atraso. Regularize para continuar.",
                    "warning",
                )
            return redirect(url_for("billing.portal"))
        return view(*args, **kwargs)

    return wrapped


def feature_required(feature_key):
    """
    Decorator que verifica se o usuário tem acesso a uma feature específica.

    Usage:
        @feature_required('multi_users')
        def my_view():
            pass
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            # Verificar se o usuário tem a feature
            if not current_user.has_feature(feature_key):
                flash(
                    f"Seu plano não inclui este recurso. Faça upgrade para acessar.",
                    "warning",
                )
                return redirect(url_for("billing.plans"))

            return view(*args, **kwargs)

        return wrapped

    return decorator
