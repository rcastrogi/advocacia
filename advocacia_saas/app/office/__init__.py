from flask import Blueprint

bp = Blueprint("office", __name__)

from app.office import routes  # noqa: E402,F401
