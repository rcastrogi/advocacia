"""
Decorators customizados para controle de acesso
"""

from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def lawyer_required(f):
    """
    Decorator que permite acesso apenas para advogados e master.
    Clientes são bloqueados.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Bloquear clientes
        if current_user.user_type == "cliente":
            flash("Acesso negado. Esta área é exclusiva para advogados.", "danger")
            abort(403)

        # Permitir master e advogado
        return f(*args, **kwargs)

    return decorated_function


def master_required(f):
    """
    Decorator que permite acesso apenas para master.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        if current_user.user_type != "master":
            flash(
                "Acesso negado. Esta área é exclusiva para administradores.", "danger"
            )
            abort(403)

        return f(*args, **kwargs)

    return decorated_function
