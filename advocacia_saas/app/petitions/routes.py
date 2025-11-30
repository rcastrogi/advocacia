from datetime import datetime
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from xhtml2pdf import pisa
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import bleach

from app import db
from app.billing.decorators import subscription_required
from app.billing.utils import (
    BillingAccessError,
    ensure_petition_type,
    record_petition_usage,
    slugify,
)
from app.models import PetitionTemplate, PetitionType
from app.petitions import bp
from app.petitions.forms import (
    CivilPetitionForm,
    FamilyPetitionForm,
    PetitionTemplateForm,
)

ATTACHMENT_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ATTACHMENT_COUNT = 5

DEFAULT_TEMPLATE_DEFINITIONS = (
    {
        "slug": "modelo-padrao-peticao-inicial",
        "name": "Petição Inicial Cível",
        "category": "civel",
        "description": "Modelo base para ações indenizatórias/obrigações.",
        "content": """
{{ forum | upper }}
{{ vara }}

Processo nº: {{ process_number or 'a ser definido' }}

{{ author_name | upper }}
{{ author_qualification }}

vem, por seus advogados, com fundamento nos artigos 186, 187 e 927 do Código Civil e demais dispositivos aplicáveis, propor a presente

AÇÃO CÍVEL

em face de {{ defendant_name.upper() }}, {{ defendant_qualification }}, pelos fatos e fundamentos a seguir expostos:

I - DOS FATOS
{{ facts }}

II - DO DIREITO
{{ fundamentos }}

III - DOS PEDIDOS
{{ pedidos }}

IV - DO VALOR DA CAUSA
{% if valor_causa %}Dá-se à causa o valor de R$ {{ '%.2f' | format(valor_causa) }}.{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}

{{ cidade }}, {{ data_assinatura }}

__________________________________
{{ advogado_nome }}
OAB {{ advogado_oab }}
""",
        "petition_type": {
            "slug": "peticao-inicial-civel",
            "name": "Petição Inicial Cível",
            "category": "civel",
            "is_billable": True,
            "base_price": Decimal("10.00"),
        },
    },
    {
        "slug": "modelo-padrao-contestacao",
        "name": "Contestação Cível",
        "category": "civel",
        "description": "Contestação geral para ações cíveis.",
        "content": """
{{ forum | upper }}
{{ vara }}

Processo nº: {{ process_number or '0000000-00.0000.0.00.0000' }}

{{ defendant_name | upper }}
{{ defendant_qualification }}

vem, respeitosamente, à presença de Vossa Excelência, por intermédio de seus advogados, apresentar

CONTESTAÇÃO

à ação proposta por {{ author_name.upper() }}, {{ author_qualification }}, expondo o que segue:

I - SÍNTESE DOS FATOS
{{ facts }}

II - PRELIMINARES
{{ fundamentos }}

III - MÉRITO
{{ pedidos }}

IV - DOS PEDIDOS FINAIS
a) rejeição total dos pedidos iniciais;
b) condenação do autor ao pagamento das custas e honorários;
c) produção de todos os meios de prova admitidos em direito.

{{ cidade }}, {{ data_assinatura }}

__________________________________
{{ advogado_nome }}
OAB {{ advogado_oab }}
""",
        "petition_type": {
            "slug": "contestacao-civel",
            "name": "Contestação Cível",
            "category": "civel",
            "is_billable": True,
            "base_price": Decimal("12.00"),
        },
    },
    {
        "slug": "modelo-familia-divorcio",
        "name": "Divórcio Consensual",
        "category": "familia",
        "description": "Petição base para divórcio com acordo de guarda e alimentos.",
        "content": """
{{ forum | upper }} - {{ vara }}

Processo nº: {{ process_number or 'a atribuir' }}

{{ spouse_one_name | upper }}
{{ spouse_one_qualification }}

e

{{ spouse_two_name | upper }}
{{ spouse_two_qualification }}

vêm, por seus advogados, propor a presente

{{ action_type | upper }}

em razão do término da união celebrada em {{ marriage_city or '...' }}{% if marriage_date %} em {{ marriage_date }}{% endif %}, sob o regime de {{ marriage_regime or 'comunhão parcial' }}.{% if prenup_summary %}

Pacto antenupcial: {{ prenup_summary }}.{% endif %}

I - DOS FATOS
{{ facts }}

II - DOS FILHOS E GUARDA
{{ children_info or 'Não há filhos menores.' }}

Proposta de guarda/convivência: {{ custody_plan or 'Guarda compartilhada conforme acordo anexo.' }}

III - DOS ALIMENTOS
{{ alimony_plan or 'As partes renunciam aos alimentos.' }}

IV - DO PATRIMÔNIO
{{ property_description or 'Não há bens a partilhar.' }}

V - DO DIREITO
{{ fundamentos }}

VI - DOS PEDIDOS
{{ pedidos }}

{{ cidade }}, {{ data_assinatura }}

__________________________________
{{ advogado_nome }}
OAB {{ advogado_oab }}
""",
        "petition_type": {
            "slug": "peticao-familia-divorcio",
            "name": "Petição Família",
            "category": "familia",
            "is_billable": True,
            "base_price": Decimal("15.00"),
        },
    },
)


def _render_pdf(text: str, title: str) -> BytesIO:
    """
    Renderiza conteúdo HTML para PDF usando xhtml2pdf.
    Suporta formatação rica: negrito, itálico, fontes, cabeçalhos, listas, etc.
    """
    # Tags HTML permitidas para sanitização
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'span', 'div', 'blockquote',
        'a', 'img'
    ]
    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'style'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan'],
    }
    
    # Sanitiza o HTML
    clean_html = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    # Template HTML completo com estilos para impressão
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            @page {{
                size: A4;
                margin: 2.5cm 2cm 2cm 3cm;
                @frame footer {{
                    -pdf-frame-content: footerContent;
                    bottom: 0.5cm;
                    margin-left: 1cm;
                    margin-right: 1cm;
                    height: 1cm;
                }}
            }}
            
            body {{
                font-family: Times, 'Times New Roman', serif;
                font-size: 12pt;
                line-height: 1.5;
                text-align: justify;
                color: #000;
            }}
            
            h1 {{
                font-size: 16pt;
                font-weight: bold;
                text-align: center;
                margin: 0 0 24pt 0;
            }}
            
            h2 {{
                font-size: 14pt;
                font-weight: bold;
                margin: 18pt 0 12pt 0;
            }}
            
            h3 {{
                font-size: 12pt;
                font-weight: bold;
                margin: 12pt 0 8pt 0;
            }}
            
            h4 {{
                font-size: 12pt;
                font-weight: bold;
                font-style: italic;
                margin: 10pt 0 6pt 0;
            }}
            
            p {{
                margin: 0 0 12pt 0;
                text-indent: 2cm;
            }}
            
            ul, ol {{
                margin: 12pt 0;
                padding-left: 1.5cm;
            }}
            
            li {{
                margin-bottom: 6pt;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 12pt 0;
            }}
            
            th, td {{
                border: 1px solid #000;
                padding: 6pt 8pt;
                text-align: left;
            }}
            
            th {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            
            strong, b {{
                font-weight: bold;
            }}
            
            em, i {{
                font-style: italic;
            }}
            
            u {{
                text-decoration: underline;
            }}
            
            blockquote {{
                margin: 12pt 2cm;
                font-style: italic;
                border-left: 3pt solid #ccc;
                padding-left: 12pt;
            }}
            
            .signature {{
                margin-top: 48pt;
                text-align: center;
            }}
            
            .signature-line {{
                border-top: 1px solid #000;
                width: 60%;
                margin: 0 auto;
                padding-top: 6pt;
            }}
            
            #footerContent {{
                font-size: 10pt;
                text-align: center;
                color: #666;
            }}
        </style>
    </head>
    <body>
        {clean_html}
        <div id="footerContent">
            <pdf:pagenumber />
        </div>
    </body>
    </html>
    """
    
    # Gera o PDF
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        src=html_template,
        dest=buffer,
        encoding='UTF-8'
    )
    
    if pisa_status.err:
        # Fallback para texto simples se houver erro
        buffer = BytesIO()
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas as reportlab_canvas
        
        pdf = reportlab_canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        x_margin = 2 * cm
        y = height - 2 * cm
        
        pdf.setTitle(title)
        pdf.setFont("Helvetica", 11)
        
        # Remove tags HTML para texto simples
        import re
        plain_text = re.sub('<[^<]+?>', '', text)
        
        for raw_line in plain_text.splitlines():
            line = raw_line.rstrip()
            if not line:
                y -= 12
            else:
                pdf.drawString(x_margin, y, line)
                y -= 14
            
            if y <= 2 * cm:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = height - 2 * cm
        
        pdf.showPage()
        pdf.save()
    
    buffer.seek(0)
    return buffer


def ensure_default_templates():
    created = False
    for data in DEFAULT_TEMPLATE_DEFINITIONS:
        if PetitionTemplate.query.filter_by(slug=data["slug"]).first():
            continue
        petition_type = ensure_petition_type(data["petition_type"])
        template = PetitionTemplate(
            slug=data["slug"],
            name=data["name"],
            description=data.get("description"),
            category=data.get("category", "civel"),
            content=data["content"].strip(),
            is_global=True,
            petition_type_id=petition_type.id,
        )
        db.session.add(template)
        created = True

    if created:
        db.session.commit()


def _accessible_templates_for(user, category: str | None = None):
    query = PetitionTemplate.query.filter(
        PetitionTemplate.is_active.is_(True),
        or_(PetitionTemplate.is_global.is_(True), PetitionTemplate.owner_id == user.id),
    )
    if category:
        query = query.filter(PetitionTemplate.category == category)
    return query.order_by(PetitionTemplate.category, PetitionTemplate.name).all()


def _extract_attachments(files):
    attachments = []
    if not files:
        return attachments

    for file_storage in files:
        if not file_storage or not getattr(file_storage, "filename", ""):
            continue

        filename = secure_filename(file_storage.filename)
        if not filename:
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ATTACHMENT_EXTENSIONS:
            raise ValueError(f"Formato não permitido para {filename}.")

        file_storage.stream.seek(0, 2)
        size = file_storage.stream.tell()
        file_storage.stream.seek(0)
        if size > MAX_ATTACHMENT_SIZE:
            raise ValueError(f"{filename} excede o limite de 5 MB.")

        attachments.append({"filename": filename, "data": file_storage.read()})

        if len(attachments) >= MAX_ATTACHMENT_COUNT:
            break

    return attachments


def _build_template_label(template: PetitionTemplate) -> str:
    scope = "Padrão" if template.is_global else "Meu modelo"
    return f"{template.name} · {template.category.title()} ({scope})"


def _populate_type_choices(form: PetitionTemplateForm):
    petition_types = PetitionType.query.order_by(
        PetitionType.category, PetitionType.name
    ).all()
    form.petition_type_id.choices = [
        (ptype.id, f"{ptype.name} ({ptype.category})") for ptype in petition_types
    ]


def _require_admin():
    if current_user.user_type != "master":
        abort(403)


def _can_manage_template(template: PetitionTemplate) -> bool:
    if template.is_global:
        return current_user.user_type == "master"
    return template.owner_id == current_user.id


def _redirect_for_template(template: PetitionTemplate):
    if template.is_global:
        return url_for("petitions.manage_global_templates")
    return url_for("petitions.personal_templates")


@bp.route("/api/template/<int:template_id>/defaults")
@login_required
def get_template_defaults(template_id):
    """API endpoint to get default values for a petition template."""
    template = PetitionTemplate.query.get_or_404(template_id)
    
    # Check if user has access to this template
    if not template.is_accessible_by(current_user):
        return jsonify({"error": "Acesso negado"}), 403
    
    # Get default values from the template
    defaults = template.get_default_values()
    
    return jsonify({
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "defaults": defaults
    })


@bp.route("/civil", methods=["GET", "POST"])
@login_required
@subscription_required
def civil_petitions():
    ensure_default_templates()
    form = CivilPetitionForm()

    templates = _accessible_templates_for(current_user)
    form.template_id.choices = [
        (template.id, _build_template_label(template)) for template in templates
    ]

    if not form.template_id.choices:
        flash(
            "Nenhum modelo disponível. Crie um modelo padrão ou pessoal para continuar.",
            "warning",
        )
        return redirect(url_for("petitions.personal_templates"))

    if not form.template_id.data and not form.is_submitted():
        form.template_id.data = form.template_id.choices[0][0]

    if form.validate_on_submit():
        template = next(
            (tpl for tpl in templates if tpl.id == form.template_id.data),
            None,
        )

        if not template:
            flash("Modelo selecionado não foi encontrado.", "error")
            return redirect(request.url)

        context = {
            "forum": form.forum.data,
            "vara": form.vara.data,
            "process_number": form.process_number.data,
            "author_name": form.author_name.data,
            "author_qualification": form.author_qualification.data,
            "defendant_name": form.defendant_name.data,
            "defendant_qualification": form.defendant_qualification.data,
            "facts": form.facts.data,
            "fundamentos": form.fundamentos.data,
            "pedidos": form.pedidos.data,
            "valor_causa": form.valor_causa.data,
            "cidade": form.cidade.data,
            "data_assinatura": form.data_assinatura.data.strftime("%d/%m/%Y"),
            "advogado_nome": form.advogado_nome.data,
            "advogado_oab": form.advogado_oab.data,
        }

        rendered_text = render_template_string(template.content, **context)
        document_title = f"Peticao-{template.slug}"
        pdf_buffer = _render_pdf(rendered_text, document_title)
        filename = f"{template.slug}-{datetime.now().strftime('%Y%m%d-%H%M')}.pdf"

        try:
            record_petition_usage(current_user, template.petition_type)
        except BillingAccessError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("billing.portal"))

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    return render_template(
        "petitions/civil/form.html",
        title="Petições Cíveis",
        form=form,
        templates=templates,
    )


@bp.route("/family", methods=["GET", "POST"])
@login_required
@subscription_required
def family_petitions():
    ensure_default_templates()
    form = FamilyPetitionForm()

    templates = _accessible_templates_for(current_user, category="familia")
    form.template_id.choices = [
        (template.id, _build_template_label(template)) for template in templates
    ]

    if not form.template_id.choices:
        flash(
            "Nenhum modelo de família disponível. Crie um modelo padrão ou pessoal para continuar.",
            "warning",
        )
        return redirect(url_for("petitions.personal_templates"))

    if not form.template_id.data and not form.is_submitted():
        form.template_id.data = form.template_id.choices[0][0]

    if form.validate_on_submit():
        template = next(
            (tpl for tpl in templates if tpl.id == form.template_id.data), None
        )

        if not template:
            flash("Modelo selecionado não foi encontrado.", "error")
            return redirect(request.url)

        try:
            attachments = _extract_attachments(form.documents.data)
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(request.url)

        context = {
            "forum": form.forum.data,
            "vara": form.vara.data,
            "process_number": form.process_number.data,
            "action_type": form.action_type.data,
            "marriage_date": form.marriage_date.data.strftime("%d/%m/%Y")
            if form.marriage_date.data
            else None,
            "marriage_city": form.marriage_city.data,
            "marriage_regime": form.marriage_regime.data,
            "prenup_summary": form.prenup_details.data
            if form.has_prenup.data
            else None,
            "spouse_one_name": form.spouse_one_name.data,
            "spouse_one_qualification": form.spouse_one_qualification.data,
            "spouse_two_name": form.spouse_two_name.data,
            "spouse_two_qualification": form.spouse_two_qualification.data,
            "children_info": form.children_info.data,
            "custody_plan": form.custody_plan.data,
            "alimony_plan": form.alimony_plan.data,
            "property_description": form.property_description.data,
            "facts": form.facts.data,
            "fundamentos": form.fundamentos.data,
            "pedidos": form.pedidos.data,
            "cidade": form.cidade.data,
            "data_assinatura": form.data_assinatura.data.strftime("%d/%m/%Y"),
            "advogado_nome": form.advogado_nome.data,
            "advogado_oab": form.advogado_oab.data,
        }

        rendered_text = render_template_string(template.content, **context)
        document_title = f"Peticao-Familia-{template.slug}"
        pdf_buffer = _render_pdf(rendered_text, document_title)
        base_filename = (
            f"{template.slug}-familia-{datetime.now().strftime('%Y%m%d-%H%M')}"
        )
        pdf_filename = f"{base_filename}.pdf"

        try:
            record_petition_usage(current_user, template.petition_type)
        except BillingAccessError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("billing.portal"))

        if attachments:
            pdf_bytes = pdf_buffer.getvalue()
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, "w") as zipf:
                zipf.writestr(pdf_filename, pdf_bytes)
                for attachment in attachments:
                    zipf.writestr(
                        f"anexos/{attachment['filename']}", attachment["data"]
                    )
            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{base_filename}-com-anexos.zip",
            )

        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=pdf_filename,
        )

    return render_template(
        "petitions/family/form.html",
        title="Petições de Família",
        form=form,
        templates=templates,
    )


@bp.route("/templates/global")
@login_required
def manage_global_templates():
    _require_admin()

    templates = (
        PetitionTemplate.query.filter_by(is_global=True)
        .order_by(PetitionTemplate.category, PetitionTemplate.name)
        .all()
    )
    return render_template(
        "petitions/templates/manage.html",
        title="Modelos padrão",
        templates=templates,
    )


@bp.route("/templates/global/new", methods=["GET", "POST"])
@login_required
def create_global_template():
    _require_admin()

    form = PetitionTemplateForm()
    _populate_type_choices(form)

    if form.validate_on_submit():
        slug = slugify(form.name.data)
        if PetitionTemplate.query.filter_by(slug=slug).first():
            flash("Já existe um modelo com esse nome.", "warning")
        else:
            template = PetitionTemplate(
                slug=slug,
                name=form.name.data,
                category=form.category.data,
                description=form.description.data,
                content=form.content.data.strip(),
                is_global=True,
                is_active=form.is_active.data,
                petition_type_id=form.petition_type_id.data,
            )
            # Save default values
            defaults = {}
            if form.default_facts.data:
                defaults["facts"] = form.default_facts.data
            if form.default_fundamentos.data:
                defaults["fundamentos"] = form.default_fundamentos.data
            if form.default_pedidos.data:
                defaults["pedidos"] = form.default_pedidos.data
            template.set_default_values(defaults)
            
            db.session.add(template)
            db.session.commit()
            flash("Modelo padrão criado com sucesso!", "success")
            return redirect(url_for("petitions.manage_global_templates"))

    return render_template(
        "petitions/templates/manage_edit.html",
        title="Novo modelo padrão",
        form=form,
        template=None,
        page_icon="fas fa-layer-group",
        page_title="Novo modelo padrão",
        page_subtitle="Crie um modelo global disponível para todos os escritórios.",
        back_url=url_for("petitions.manage_global_templates"),
        submit_label="Salvar modelo",
    )


@bp.route("/templates/personal")
@login_required
def personal_templates():
    templates = (
        PetitionTemplate.query.filter_by(owner_id=current_user.id)
        .order_by(PetitionTemplate.created_at.desc())
        .all()
    )
    return render_template(
        "petitions/templates/personal.html",
        title="Meus modelos",
        templates=templates,
    )


@bp.route("/templates/personal/new", methods=["GET", "POST"])
@login_required
def create_personal_template():
    form = PetitionTemplateForm()
    _populate_type_choices(form)

    if form.validate_on_submit():
        slug = slugify(f"{current_user.id}-{form.name.data}")
        template = PetitionTemplate(
            slug=slug,
            name=form.name.data,
            category=form.category.data,
            description=form.description.data,
            content=form.content.data.strip(),
            is_global=False,
            is_active=form.is_active.data,
            owner_id=current_user.id,
            petition_type_id=form.petition_type_id.data,
        )
        # Save default values
        defaults = {}
        if form.default_facts.data:
            defaults["facts"] = form.default_facts.data
        if form.default_fundamentos.data:
            defaults["fundamentos"] = form.default_fundamentos.data
        if form.default_pedidos.data:
            defaults["pedidos"] = form.default_pedidos.data
        template.set_default_values(defaults)
        
        db.session.add(template)
        db.session.commit()
        flash("Modelo pessoal criado com sucesso!", "success")
        return redirect(url_for("petitions.personal_templates"))

    return render_template(
        "petitions/templates/manage_edit.html",
        title="Novo modelo do escritório",
        form=form,
        template=None,
        page_icon="fas fa-file-circle-plus",
        page_title="Novo modelo do escritório",
        page_subtitle="Crie um modelo privado para o seu escritório reaproveitar em petições.",
        back_url=url_for("petitions.personal_templates"),
        submit_label="Salvar modelo",
    )


@bp.route("/templates/<int:template_id>")
@login_required
def view_template(template_id):
    template = PetitionTemplate.query.get_or_404(template_id)
    if not template.is_accessible_by(current_user):
        abort(403)

    return render_template(
        "petitions/templates/detail.html",
        title=f"Modelo: {template.name}",
        template=template,
    )


@bp.route("/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def edit_template(template_id):
    template = PetitionTemplate.query.get_or_404(template_id)
    if not _can_manage_template(template):
        abort(403)

    form = PetitionTemplateForm(obj=template)
    _populate_type_choices(form)

    if request.method == "GET":
        form.petition_type_id.data = template.petition_type_id
        # Load default values into form
        defaults = template.get_default_values()
        form.default_facts.data = defaults.get("facts", "")
        form.default_fundamentos.data = defaults.get("fundamentos", "")
        form.default_pedidos.data = defaults.get("pedidos", "")

    if form.validate_on_submit():
        template.name = form.name.data
        template.description = form.description.data
        template.category = form.category.data
        template.content = form.content.data.strip()
        template.is_active = form.is_active.data
        template.petition_type_id = form.petition_type_id.data
        
        # Save default values
        defaults = {}
        if form.default_facts.data:
            defaults["facts"] = form.default_facts.data
        if form.default_fundamentos.data:
            defaults["fundamentos"] = form.default_fundamentos.data
        if form.default_pedidos.data:
            defaults["pedidos"] = form.default_pedidos.data
        template.set_default_values(defaults)
        
        db.session.commit()
        flash("Modelo atualizado com sucesso!", "success")
        return redirect(_redirect_for_template(template))

    return render_template(
        "petitions/templates/manage_edit.html",
        title=f"Editar modelo: {template.name}",
        form=form,
        template=template,
        page_icon="fas fa-pen-to-square",
        page_title="Editar modelo",
        page_subtitle=f'Atualize o conteúdo e os metadados de "{template.name}".',
        back_url=_redirect_for_template(template),
        submit_label="Salvar alterações",
    )


@bp.route("/templates/<int:template_id>/toggle", methods=["POST"])
@login_required
def toggle_template(template_id):
    template = PetitionTemplate.query.get_or_404(template_id)
    if not _can_manage_template(template):
        abort(403)

    template.is_active = not template.is_active
    db.session.commit()
    flash("Status do modelo atualizado!", "success")
    return redirect(_redirect_for_template(template))


@bp.route("/templates/examples")
@login_required
def template_examples():
    sample_context = {
        "forum": "Fórum Central",
        "vara": "2ª Vara Cível",
        "author_name": "Fulana de Tal",
        "defendant_name": "Beltrano",
        "valor_causa": Decimal("50000.00"),
        "pedidos": ["Condenação em danos morais", "Pagamento de custas"],
        "cidade": "São Paulo",
        "data_assinatura": datetime.now().strftime("%d/%m/%Y"),
    }
    full_snippet = """
{{ forum | upper }} - {{ vara }}

AUTOR: {{ author_name }}
RÉU: {{ defendant_name }}

{% if valor_causa %}
Valor da causa: R$ {{ '%.2f'|format(valor_causa) }}
{% endif %}

Pedidos:
{% for pedido in pedidos %}
 - {{ loop.index }}. {{ pedido }}
{% endfor %}

{{ cidade }}, {{ data_assinatura }}
"""
    rendered_example = render_template_string(full_snippet, **sample_context)

    mini_examples = [
        {
            "title": "Inserindo variáveis",
            "code": "Cliente: {{ author_name }} / Réu: {{ defendant_name }}",
        },
        {
            "title": "Condição simples",
            "code": "{% if valor_causa %}Valor: R$ {{ valor_causa }}{% else %}Sem valor definido{% endif %}",
        },
        {
            "title": "Loop numerado",
            "code": "{% for pedido in pedidos %}\n{{ loop.index }}. {{ pedido }}\n{% endfor %}",
        },
        {
            "title": "Filtros úteis",
            "code": "{{ forum|upper }} / {{ cidade|title }} / {{ pedidos|length }} pedidos",
        },
    ]

    return render_template(
        "petitions/templates/examples.html",
        title="Exemplos de Jinja",
        mini_examples=mini_examples,
        sample_context=sample_context,
        full_snippet=full_snippet.strip(),
        rendered_example=rendered_example.strip(),
    )
