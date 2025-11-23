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

        if not plan or plan.status != "active" or current_user.is_delinquent:
            flash(
                "Sua assinatura está inativa ou em atraso. Regularize para continuar.",
                "warning",
            )
            return redirect(url_for("billing.portal"))
        return view(*args, **kwargs)

    return wrapped
