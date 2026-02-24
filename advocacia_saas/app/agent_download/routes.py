"""Rotas de download do Petitio Assinador."""

from flask import render_template, redirect
from flask_login import login_required

from app.agent_download import bp

# URL do release no GitHub (atualizar após publicar release)
GITHUB_RELEASE_URL = "https://github.com/rcastrogi/advocacia/releases/latest"
DOWNLOAD_URL = "https://github.com/rcastrogi/advocacia/releases/latest/download/PetitioAssinador-v1.0.0-win64.zip"
AGENT_VERSION = "1.0.0"


@bp.route('/')
@login_required
def index():
    """Página de download do Petitio Assinador."""
    return render_template(
        'agent_download/download.html',
        agent_version=AGENT_VERSION,
        download_url=DOWNLOAD_URL,
        github_url=GITHUB_RELEASE_URL,
    )


@bp.route('/download')
@login_required
def download():
    """Redireciona para o download direto."""
    return redirect(DOWNLOAD_URL)
