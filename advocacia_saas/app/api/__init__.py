from flask import Blueprint

bp = Blueprint("api", __name__)

from app.api import (
    onboarding,  # noqa: E402,F401
    routes,  # noqa: E402,F401
)
