"""Blueprint para download do Petitio Assinador."""

from flask import Blueprint

bp = Blueprint(
    'agent_download',
    __name__,
    template_folder='templates',
    url_prefix='/agent',
)

from app.agent_download import routes  # noqa: E402, F401
