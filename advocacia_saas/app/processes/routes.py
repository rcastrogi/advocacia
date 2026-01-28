"""
Processes Routes - Rotas HTTP para processos judiciais.

Controllers delegando para os serviços especializados.
"""

import re
from datetime import datetime, timezone

from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from jinja2 import Template

from app import db
from app.decorators import lawyer_required
from app.models import Client, FeeContractTemplate
from app.petitions.services import PDFGenerationService
from app.processes import bp
from app.processes.forms import ProcessForm
from app.processes.services import ProcessService


def _sanitize_text(text: str, max_length: int = 255) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", str(text).strip())
    return text[:max_length]


def _get_default_fee_contract_template(user_id: int) -> FeeContractTemplate:
    default_template = FeeContractTemplate.query.filter_by(
        user_id=user_id, is_default=True
    ).first()
    if default_template:
        return default_template

    template_content = """
<h1>CONTRATO DE HONORÁRIOS ADVOCATÍCIOS</h1>

<p>Pelo presente instrumento particular, de um lado:</p>

<p><strong>CONTRATANTE:</strong> {{ client_name }}, inscrito(a) no CPF/CNPJ sob nº {{ client_document }},
residente e domiciliado(a) em {{ client_address }}.</p>

<p><strong>CONTRATADO(A):</strong> {{ lawyer_name }}, OAB {{ lawyer_oab }},
com endereço profissional em {{ lawyer_address }}.</p>

<p>As partes acima identificadas têm, entre si, justo e contratado o seguinte:</p>

<h2>1. OBJETO</h2>
<p>{{ contract_object }}</p>

<h2>2. HONORÁRIOS</h2>
<p>O(s) honorário(s) será(ão) fixado(s) na modalidade <strong>{{ fee_type }}</strong> no valor de
<strong>{{ fee_value }}</strong>.</p>

{% if success_fee_percent %}
<p>Além disso, será devido honorário de êxito no percentual de <strong>{{ success_fee_percent }}%</strong>,
quando aplicável.</p>
{% endif %}

<h2>3. FORMA DE PAGAMENTO</h2>
<p>{{ payment_terms }}</p>

<h2>4. PRAZO E RESCISÃO</h2>
<p>O presente contrato vigerá até o término do serviço contratado, podendo ser rescindido
mediante aviso prévio por escrito.</p>

<h2>5. FORO</h2>
<p>Fica eleito o foro da comarca de {{ forum_city }} - {{ forum_state }} para dirimir quaisquer dúvidas
oriundas deste contrato.</p>

<p>{{ signature_city }}, {{ signature_date }}.</p>

<br><br>
<p>__________________________________________</p>
<p>{{ client_name }}<br>CONTRATANTE</p>

<br>
<p>__________________________________________</p>
<p>{{ lawyer_name }}<br>CONTRATADO(A)</p>
"""

    default_template = FeeContractTemplate(
        user_id=user_id,
        name="Modelo Padrão",
        content=template_content.strip(),
        is_default=True,
    )
    db.session.add(default_template)
    db.session.commit()
    return default_template


@bp.route("/")
@login_required
@lawyer_required
def dashboard():
    """Dashboard principal de processos."""
    data = ProcessService.get_dashboard_data(current_user.id)

    return render_template(
        "processes/dashboard.html",
        title="Processos - Dashboard",
        **data,
    )


@bp.route("/list")
@login_required
@lawyer_required
def list_processes():
    """Lista todos os processos."""
    data = ProcessService.list_processes(
        user_id=current_user.id,
        status=request.args.get("status"),
        search=request.args.get("search"),
        per_page=20,
    )

    return render_template(
        "processes/list.html",
        title="Lista de Processos",
        **data,
    )


@bp.route("/pending-petitions")
@login_required
@lawyer_required
def pending_petitions():
    """Lista petições sem número de processo."""
    page = request.args.get("page", 1, type=int)
    petitions = ProcessService.get_pending_petitions(current_user.id, page)

    return render_template(
        "processes/pending_petitions.html",
        title="Petições Pendentes de Número",
        petitions=petitions,
    )


@bp.route("/reports")
@login_required
@lawyer_required
def reports():
    """Página de relatórios de processos."""
    return render_template("processes/reports.html", title="Relatórios de Processos")


# =============================================================================
# CRUD de Processos
# =============================================================================


@bp.route("/new", methods=["GET", "POST"])
@login_required
@lawyer_required
def create():
    """Criar novo processo."""
    form = ProcessForm()
    form.client_id.choices = ProcessService.get_client_choices(current_user.id)

    if form.validate_on_submit():
        result = ProcessService.create_process(
            user_id=current_user.id,
            title=form.title.data,
            process_number=form.process_number.data,
            plaintiff=form.plaintiff.data,
            defendant=form.defendant.data,
            client_id=form.client_id.data,
            court=form.court.data,
            court_instance=form.court_instance.data,
            jurisdiction=form.jurisdiction.data,
            district=form.district.data,
            judge=form.judge.data,
            status=form.status.data,
            distribution_date=form.distribution_date.data,
            next_deadline=form.next_deadline.data,
            deadline_description=form.deadline_description.data,
            priority=form.priority.data,
        )

        if not result.success:
            flash(result.error_message, "danger")
            return render_template(
                "processes/form.html",
                title="Novo Processo",
                form=form,
                is_edit=False,
            )

        flash(f"Processo '{result.process.title}' criado com sucesso!", "success")
        return redirect(url_for("processes.view", process_id=result.process.id))

    return render_template(
        "processes/form.html",
        title="Novo Processo",
        form=form,
        is_edit=False,
    )


@bp.route("/<int:process_id>")
@login_required
@lawyer_required
def view(process_id):
    """Visualizar detalhes do processo."""
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

    # Buscar petições vinculadas
    petitions = process.petitions

    # Buscar movimentações (se existir)
    movements = []
    if hasattr(process, "movements"):
        from app.models import ProcessMovement

        movements = (
            process.movements.order_by(ProcessMovement.created_at.desc())
            .limit(10)
            .all()
        )

    return render_template(
        "processes/view.html",
        title=f"Processo: {process.title}",
        process=process,
        petitions=petitions,
        movements=movements,
    )


@bp.route("/<int:process_id>/edit", methods=["GET", "POST"])
@login_required
@lawyer_required
def edit(process_id):
    """Editar processo existente."""
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

    form = ProcessForm(obj=process)
    form.client_id.choices = ProcessService.get_client_choices(current_user.id)

    if form.validate_on_submit():
        result = ProcessService.update_process(
            process=process,
            title=form.title.data,
            process_number=form.process_number.data,
            plaintiff=form.plaintiff.data or None,
            defendant=form.defendant.data or None,
            client_id=form.client_id.data or None,
            court=form.court.data or None,
            court_instance=form.court_instance.data or None,
            jurisdiction=form.jurisdiction.data or None,
            district=form.district.data or None,
            judge=form.judge.data or None,
            status=form.status.data,
            distribution_date=form.distribution_date.data,
            next_deadline=form.next_deadline.data,
            deadline_description=form.deadline_description.data or None,
            priority=form.priority.data,
        )

        if not result.success:
            flash(result.error_message, "danger")
            return render_template(
                "processes/form.html",
                title=f"Editar: {process.title}",
                form=form,
                process=process,
                is_edit=True,
            )

        flash("Processo atualizado com sucesso!", "success")
        return redirect(url_for("processes.view", process_id=process.id))

    # Preencher client_id como string para o select
    if process.client_id:
        form.client_id.data = str(process.client_id)

    return render_template(
        "processes/form.html",
        title=f"Editar: {process.title}",
        form=form,
        process=process,
        is_edit=True,
    )


@bp.route("/<int:process_id>/delete", methods=["POST"])
@login_required
@lawyer_required
def delete(process_id):
    """Excluir processo."""
    process = ProcessService.get_process(process_id, current_user.id)
    if not process:
        flash("Processo não encontrado.", "danger")
        return redirect(url_for("processes.list_processes"))

    title = ProcessService.delete_process(process)
    flash(f"Processo '{title}' excluído com sucesso.", "success")
    return redirect(url_for("processes.list_processes"))


# =============================================================================
# CONTRATO DE HONORÁRIOS
# =============================================================================


@bp.route("/fee-contracts")
@login_required
@lawyer_required
def fee_contracts():
    """Lista modelos de contrato de honorários."""
    templates = (
        FeeContractTemplate.query.filter_by(user_id=current_user.id)
        .order_by(FeeContractTemplate.is_default.desc(), FeeContractTemplate.name.asc())
        .all()
    )

    if not templates:
        _get_default_fee_contract_template(current_user.id)
        templates = FeeContractTemplate.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "processes/fee_contracts.html",
        title="Contratos de Honorários",
        templates=templates,
    )


@bp.route("/fee-contracts/new", methods=["GET", "POST"])
@login_required
@lawyer_required
def fee_contract_new():
    """Criar novo modelo de contrato de honorários."""
    if request.method == "POST":
        name = _sanitize_text(request.form.get("name", ""), max_length=200)
        content = request.form.get("content", "").strip()

        if not name or not content:
            flash("Nome e conteúdo são obrigatórios.", "danger")
            return redirect(url_for("processes.fee_contract_new"))

        template = FeeContractTemplate(
            user_id=current_user.id,
            name=name,
            content=content,
            is_default=False,
        )
        db.session.add(template)
        db.session.commit()

        flash("Modelo criado com sucesso!", "success")
        return redirect(url_for("processes.fee_contracts"))

    return render_template(
        "processes/fee_contract_edit.html",
        title="Novo Modelo de Contrato",
        template=None,
    )


@bp.route("/fee-contracts/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
@lawyer_required
def fee_contract_edit(template_id):
    """Editar modelo de contrato de honorários."""
    template = FeeContractTemplate.query.filter_by(
        id=template_id, user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        name = _sanitize_text(request.form.get("name", ""), max_length=200)
        content = request.form.get("content", "").strip()

        if not name or not content:
            flash("Nome e conteúdo são obrigatórios.", "danger")
            return redirect(
                url_for("processes.fee_contract_edit", template_id=template.id)
            )

        template.name = name
        template.content = content
        template.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        flash("Modelo atualizado com sucesso!", "success")
        return redirect(url_for("processes.fee_contracts"))

    return render_template(
        "processes/fee_contract_edit.html",
        title="Editar Modelo de Contrato",
        template=template,
    )


@bp.route("/fee-contracts/generate", methods=["GET", "POST"])
@login_required
@lawyer_required
def fee_contract_generate():
    """Gerar contrato de honorários em PDF."""
    templates = (
        FeeContractTemplate.query.filter_by(user_id=current_user.id)
        .order_by(FeeContractTemplate.is_default.desc(), FeeContractTemplate.name.asc())
        .all()
    )
    if not templates:
        templates = [_get_default_fee_contract_template(current_user.id)]

    clients = (
        Client.query.filter_by(lawyer_id=current_user.id)
        .order_by(Client.full_name.asc())
        .all()
    )

    if request.method == "POST":
        template_id = request.form.get("template_id", type=int)
        template = FeeContractTemplate.query.filter_by(
            id=template_id, user_id=current_user.id
        ).first()

        if not template:
            flash("Selecione um modelo válido.", "danger")
            return redirect(url_for("processes.fee_contract_generate"))

        client_name = _sanitize_text(request.form.get("client_name", ""), 200)
        client_document = _sanitize_text(request.form.get("client_document", ""), 50)
        client_address = _sanitize_text(request.form.get("client_address", ""), 255)

        lawyer_name = _sanitize_text(request.form.get("lawyer_name", ""), 200)
        lawyer_oab = _sanitize_text(request.form.get("lawyer_oab", ""), 50)
        lawyer_address = _sanitize_text(request.form.get("lawyer_address", ""), 255)

        contract_object = _sanitize_text(request.form.get("contract_object", ""), 1000)
        fee_type = _sanitize_text(request.form.get("fee_type", ""), 50)
        fee_value = _sanitize_text(request.form.get("fee_value", ""), 100)
        payment_terms = _sanitize_text(request.form.get("payment_terms", ""), 1000)
        success_fee_percent = _sanitize_text(
            request.form.get("success_fee_percent", ""), 10
        )

        forum_city = _sanitize_text(request.form.get("forum_city", ""), 100)
        forum_state = _sanitize_text(request.form.get("forum_state", ""), 2)
        signature_city = _sanitize_text(request.form.get("signature_city", ""), 100)
        signature_date = _sanitize_text(request.form.get("signature_date", ""), 30)

        if not signature_date:
            signature_date = datetime.now(timezone.utc).strftime("%d/%m/%Y")

        context = {
            "client_name": client_name,
            "client_document": client_document,
            "client_address": client_address,
            "lawyer_name": lawyer_name,
            "lawyer_oab": lawyer_oab,
            "lawyer_address": lawyer_address,
            "contract_object": contract_object,
            "fee_type": fee_type,
            "fee_value": fee_value,
            "payment_terms": payment_terms,
            "success_fee_percent": success_fee_percent,
            "forum_city": forum_city,
            "forum_state": forum_state,
            "signature_city": signature_city,
            "signature_date": signature_date,
        }

        try:
            rendered = Template(template.content).render(**context)
            html_content = f"""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {{ margin: 2.5cm 3cm; }}
                    body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; text-align: justify; }}
                    h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                    h2 {{ font-size: 12pt; margin-top: 18pt; }}
                    p {{ margin-bottom: 12pt; text-indent: 2cm; }}
                </style>
            </head>
            <body>
                {rendered}
            </body>
            </html>
            """

            pdf_buffer = PDFGenerationService.render_pdf_from_html(
                html_content, "Contrato de Honorários"
            )

            filename = (
                f"contrato_honorarios_{client_name or 'cliente'}"
                f"_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            return send_file(
                pdf_buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )
        except Exception as e:
            flash(f"Erro ao gerar PDF: {str(e)}", "danger")
            return redirect(url_for("processes.fee_contract_generate"))

    return render_template(
        "processes/fee_contract_generate.html",
        title="Gerador de Contrato de Honorários",
        templates=templates,
        clients=clients,
    )
