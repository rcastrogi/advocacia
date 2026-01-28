"""
Gerador de Procurações
"""

from flask import render_template, request, send_file
from flask_login import current_user, login_required

from app.decorators import lawyer_required
from app.models import User
from app.procuracao import bp
from app.procuracao.repository import ClientForProcuracaoRepository
from app.procuracao.services import ProcuracaoService


@bp.route("/")
@login_required
@lawyer_required
def index():
    """Lista de procurações disponíveis"""
    powers = ProcuracaoService.get_available_powers()
    return render_template("procuracao/index.html", powers=powers)


@bp.route("/nova", methods=["GET", "POST"])
@login_required
@lawyer_required
def nova():
    """Formulário para criar nova procuração"""
    if request.method == "POST":
        client_id = request.form.get("client_id")
        tipo = request.form.get("tipo", "ad_judicia")
        poderes_especiais = request.form.get("poderes_especiais", "")

        client = ClientForProcuracaoRepository.get_by_id(client_id)
        if not client:
            return render_template("errors/404.html"), 404

        if client.user_id:
            user = User.query.get(client.user_id)
            if user and user.user_type == "master":
                return render_template("errors/403.html"), 403

        # Mapear tipo para poderes
        if tipo == "ad_judicia":
            powers = [
                "poderes gerais para o foro em geral",
                "propor e acompanhar ações de qualquer natureza",
                "apresentar defesas, contestações, recursos",
                "transigir, desistir, renunciar, receber e dar quitação",
                "substabelecer com ou sem reserva de poderes",
            ]
        else:
            powers = [
                "representar em negociações",
                "assinar documentos e contratos",
                "realizar pagamentos e recebimentos",
            ]

        # Adicionar poderes especiais se informados
        if poderes_especiais:
            powers.append(poderes_especiais)

        # Gerar PDF usando o service
        pdf_buffer = ProcuracaoService.generate_from_client(
            client=client,
            lawyer_name=current_user.full_name or current_user.username,
            lawyer_oab=current_user.oab_number or "",
            lawyer_oab_uf=current_user.uf or "SP",
            powers=powers,
            purpose=f"Procuração {tipo.replace('_', ' ').upper()}",
        )

        # Retornar PDF para download
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"procuracao_{client.full_name.replace(' ', '_')}.pdf",
        )

    # GET - mostrar formulário
    clients = ClientForProcuracaoRepository.get_by_lawyer_ordered(current_user.id)
    return render_template("procuracao/nova.html", clients=clients)
