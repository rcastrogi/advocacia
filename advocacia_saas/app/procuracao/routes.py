"""
Gerador de Procurações
"""

from datetime import datetime
from io import BytesIO

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app import db
from app.decorators import lawyer_required
from app.models import Client
from app.procuracao import bp


@bp.route("/")
@login_required
@lawyer_required
def index():
    """Lista de procurações disponíveis"""
    return render_template("procuracao/index.html")


@bp.route("/nova", methods=["GET", "POST"])
@login_required
@lawyer_required
def nova():
    """Formulário para criar nova procuração"""
    if request.method == "POST":
        client_id = request.form.get("client_id")
        tipo = request.form.get("tipo", "ad_judicia")
        poderes_especiais = request.form.get("poderes_especiais", "")

        client = Client.query.get_or_404(client_id)

        # Gerar PDF da procuração
        pdf_buffer = gerar_procuracao_pdf(
            client=client,
            advogado=current_user,
            tipo=tipo,
            poderes_especiais=poderes_especiais,
        )

        # Retornar PDF para download
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"procuracao_{client.full_name.replace(' ', '_')}.pdf",
        )

    # GET - mostrar formulário
    clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.full_name)
        .all()
    )
    return render_template("procuracao/nova.html", clients=clients)


def gerar_procuracao_pdf(client, advogado, tipo="ad_judicia", poderes_especiais=""):
    """
    Gera PDF da procuração

    Args:
        client: Objeto Client
        advogado: Objeto User (advogado)
        tipo: 'ad_judicia' ou 'ad_negotia'
        poderes_especiais: Texto com poderes especiais adicionais
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    # Estilos
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor="black",
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontSize=12,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=18,
    )

    # Conteúdo
    story = []

    # Título
    titulo = (
        "PROCURAÇÃO AD JUDICIA" if tipo == "ad_judicia" else "PROCURAÇÃO AD NEGOTIA"
    )
    story.append(Paragraph(titulo, title_style))
    story.append(Spacer(1, 0.5 * cm))

    # Outorgante
    outorgante = f"""
    <b>OUTORGANTE:</b> {client.full_name}, {client.nationality or "brasileiro(a)"}, 
    {client.civil_status or "estado civil não informado"}, {client.profession or "profissão não informada"}, 
    portador(a) do CPF/CNPJ nº {client.cpf_cnpj}, residente e domiciliado(a) em {client.street or "endereço não informado"}, 
    {client.number or ""}, {client.neighborhood or ""}, {client.city or ""}/{client.uf or ""}.
    """
    story.append(Paragraph(outorgante, body_style))
    story.append(Spacer(1, 0.3 * cm))

    # Outorgado
    outorgado = f"""
    <b>OUTORGADO:</b> {advogado.full_name}, {advogado.nationality or "brasileiro(a)"}, 
    advogado(a), inscrito(a) na OAB/{advogado.oab_number or "OAB não informada"}, 
    com escritório profissional localizado em {advogado.address or "endereço não informado"}.
    """
    story.append(Paragraph(outorgado, body_style))
    story.append(Spacer(1, 0.5 * cm))

    # Poderes
    if tipo == "ad_judicia":
        poderes_texto = """
        Pelo presente instrumento particular, o(a) OUTORGANTE constitui e nomeia seu bastante 
        procurador(a) o(a) OUTORGADO(A), a quem confere amplos poderes para:
        <br/><br/>
        Representar o(a) OUTORGANTE perante quaisquer órgãos públicos, entidades autárquicas, 
        juízos, tribunais e instâncias em geral, podendo propor e acompanhar ações de qualquer 
        natureza, defender seus interesses, apresentar defesas, contestações, reconvenções, 
        recursos de qualquer espécie, produzir provas, requerer perícias, arrolar, contraditar 
        e reinquirir testemunhas, firmar compromissos, desistir, renunciar ao direito sobre que 
        se funda a ação, transigir, receber e dar quitação, substabelecer esta procuração, com 
        ou sem reserva de iguais poderes, enfim, praticar todos os atos necessários ao fiel 
        cumprimento do presente mandato.
        """
    else:
        poderes_texto = """
        Pelo presente instrumento particular, o(a) OUTORGANTE constitui e nomeia seu bastante 
        procurador(a) o(a) OUTORGADO(A), a quem confere poderes para:
        <br/><br/>
        Representar o(a) OUTORGANTE em negociações, assinar documentos, firmar contratos, 
        realizar pagamentos e recebimentos em seu nome, movimentar contas bancárias, e praticar 
        todos os atos necessários à boa e fiel execução do presente mandato.
        """

    story.append(Paragraph(poderes_texto, body_style))

    # Poderes especiais
    if poderes_especiais:
        story.append(Spacer(1, 0.3 * cm))
        poderes_esp = f"""
        <b>PODERES ESPECIAIS:</b><br/>
        {poderes_especiais}
        """
        story.append(Paragraph(poderes_esp, body_style))

    # Data e local
    story.append(Spacer(1, 1 * cm))
    data_atual = datetime.now().strftime("%d de %B de %Y")
    local = advogado.city or "São Paulo"

    local_data = f"{local}, {data_atual}."
    story.append(Paragraph(local_data, body_style))

    # Assinatura
    story.append(Spacer(1, 2 * cm))

    assinatura = """
    <br/>
    _____________________________________________<br/>
    <b>{}</b><br/>
    CPF/CNPJ: {}
    """.format(client.full_name, client.cpf_cnpj)

    story.append(
        Paragraph(
            assinatura,
            ParagraphStyle("Signature", parent=body_style, alignment=TA_CENTER),
        )
    )

    # Gerar PDF
    doc.build(story)
    buffer.seek(0)

    return buffer
