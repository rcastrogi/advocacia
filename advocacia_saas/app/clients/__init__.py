from flask import Blueprint

bp = Blueprint("clients", __name__)

from app.clients import routes  # noqa: E402,F401
