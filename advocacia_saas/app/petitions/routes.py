from datetime import datetime
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

import bleach
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
from sqlalchemy import or_
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa

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
    SimplePetitionForm,
)

ATTACHMENT_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
MAX_ATTACHMENT_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ATTACHMENT_COUNT = 5

DEFAULT_TEMPLATE_DEFINITIONS = (
    {
        "slug": "modelo-padrao-peticao-inicial",
        "name": "Petição Cível",
        "category": "civel",
        "description": "Modelo base para ações indenizatórias/obrigações.",
        "content": """
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or 'a ser definido' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ author_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ author_qualification }}</p>

<p style="text-indent: 0;">vem, por seus advogados, com fundamento nos artigos 186, 187 e 927 do Código Civil e demais dispositivos aplicáveis, propor a presente</p>

<h1>AÇÃO CÍVEL</h1>

<p style="text-indent: 0;">em face de <strong>{{ defendant_name | upper }}</strong>, {{ defendant_qualification }}, pelos fatos e fundamentos a seguir expostos:</p>

<h2>I - DOS FATOS</h2>
{{ facts }}

<h2>II - DO DIREITO</h2>
{{ fundamentos }}

<h2>III - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
{{ pedidos }}

<h2>IV - DO VALOR DA CAUSA</h2>
<p class="valor-causa">{% if valor_causa %}Dá-se à causa o valor de <strong>R$ {{ '%.2f' | format(valor_causa) }}</strong> ({{ valor_causa | int }} reais).{% else %}Requer a atribuição do valor que Vossa Excelência entender pertinente.{% endif %}</p>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
""",
        "petition_type": {
            "slug": "peticao-inicial-civel",
            "name": "Petição Cível",
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
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or '0000000-00.0000.0.00.0000' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ defendant_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ defendant_qualification }}</p>

<p style="text-indent: 0;">vem, respeitosamente, à presença de Vossa Excelência, por intermédio de seus advogados, apresentar</p>

<h1>CONTESTAÇÃO</h1>

<p style="text-indent: 0;">à ação proposta por <strong>{{ author_name | upper }}</strong>, {{ author_qualification }}, expondo o que segue:</p>

<h2>I - SÍNTESE DOS FATOS</h2>
{{ facts }}

<h2>II - PRELIMINARES</h2>
{{ fundamentos }}

<h2>III - DO MÉRITO</h2>
{{ pedidos }}

<h2>IV - DOS PEDIDOS FINAIS</h2>
<p style="text-indent: 0;">Ante o exposto, requer:</p>
<ol type="a">
<li>A rejeição total dos pedidos iniciais;</li>
<li>A condenação do autor ao pagamento das custas processuais e honorários advocatícios;</li>
<li>A produção de todos os meios de prova admitidos em direito, especialmente o depoimento pessoal do autor, oitiva de testemunhas e prova pericial.</li>
</ol>

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pede deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
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
<div class="header">
<p class="header-forum">{{ forum | upper }}</p>
<p class="header-vara">{{ vara }}</p>
</div>

<p style="text-indent: 0;">Processo nº: {{ process_number or 'a atribuir' }}</p>

<p class="party-name" style="text-indent: 0; margin-top: 24pt;">{{ spouse_one_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ spouse_one_qualification }}</p>

<p style="text-indent: 0; margin: 12pt 0;"><strong>e</strong></p>

<p class="party-name" style="text-indent: 0;">{{ spouse_two_name | upper }}</p>
<p class="party-qualification" style="text-indent: 0;">{{ spouse_two_qualification }}</p>

<p style="text-indent: 0; margin-top: 18pt;">vêm, por seus advogados, propor a presente</p>

<h1>{{ action_type | upper }}</h1>

<p>em razão do término da união celebrada em {{ marriage_city or '...' }}{% if marriage_date %} em {{ marriage_date }}{% endif %}, sob o regime de <strong>{{ marriage_regime or 'comunhão parcial de bens' }}</strong>.{% if prenup_summary %} Pacto antenupcial: {{ prenup_summary }}.{% endif %}</p>

<h2>I - DOS FATOS</h2>
{{ facts }}

<h2>II - DOS FILHOS E DA GUARDA</h2>
<p>{{ children_info or 'Não há filhos menores ou incapazes.' }}</p>
<p><strong>Proposta de guarda e convivência:</strong> {{ custody_plan or 'Guarda compartilhada conforme acordo anexo.' }}</p>

<h2>III - DOS ALIMENTOS</h2>
<p>{{ alimony_plan or 'As partes renunciam aos alimentos recíprocos.' }}</p>

<h2>IV - DO PATRIMÔNIO</h2>
<p>{{ property_description or 'Não há bens a partilhar ou os bens serão objeto de ação própria.' }}</p>

<h2>V - DO DIREITO</h2>
{{ fundamentos }}

<h2>VI - DOS PEDIDOS</h2>
<p style="text-indent: 0;">Ante o exposto, requerem:</p>
{{ pedidos }}

<p style="text-indent: 0; margin-top: 18pt;">Nestes termos,<br>Pedem deferimento.</p>

<div class="signature-block">
<p class="signature-city-date">{{ cidade }}, {{ data_assinatura }}</p>
<div class="signature-line">
<p class="signature-name">{{ advogado_nome }}</p>
<p class="signature-oab">OAB {{ advogado_oab }}</p>
</div>
</div>
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
    Otimizado para documentos jurídicos profissionais.
    """
    import re

    # Tags HTML permitidas para sanitização
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "strike",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "span",
        "div",
        "blockquote",
        "a",
        "img",
        "hr",
        "sub",
        "sup",
    ]
    ALLOWED_ATTRIBUTES = {
        "*": ["class", "style"],
        "a": ["href", "title"],
        "img": ["src", "alt", "width", "height"],
        "td": ["colspan", "rowspan"],
        "th": ["colspan", "rowspan"],
    }

    # Sanitiza o HTML
    clean_html = bleach.clean(
        text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True
    )

    # Pré-processamento do HTML para melhor formatação
    # 1. Converte quebras de linha simples em parágrafos
    lines = clean_html.split("\n")
    processed_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # Se não está dentro de uma tag de bloco, envolve em <p>
            if not re.match(
                r"^<(p|h[1-6]|ul|ol|li|table|tr|th|td|div|blockquote)", line, re.I
            ):
                if not line.startswith("<"):
                    line = f"<p>{line}</p>"
            processed_lines.append(line)

    clean_html = "\n".join(processed_lines)

    # 2. Corrige parágrafos vazios e <br> excessivos
    clean_html = re.sub(r"<p>\s*</p>", "", clean_html)
    clean_html = re.sub(r"(<br\s*/?>){3,}", "<br><br>", clean_html)

    # 3. Adiciona classe para seções (I -, II -, DOS, DA, DO)
    clean_html = re.sub(
        r"<p>(\s*)(I+\s*[-–—]|[IVXLC]+\s*[-–—]|D[OAE]\s+|D[OA]S?\s+)",
        r'<p class="section-title">\1\2',
        clean_html,
    )

    # Template HTML completo com estilos profissionais para documentos jurídicos
    html_template = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            @page {{
                size: A4;
                margin: 3cm 2.5cm 2.5cm 3cm;
                @frame footer {{
                    -pdf-frame-content: footerContent;
                    bottom: 1cm;
                    margin-left: 2cm;
                    margin-right: 2cm;
                    height: 1cm;
                }}
            }}
            
            body {{
                font-family: 'Times New Roman', Times, serif;
                font-size: 12pt;
                line-height: 1.8;
                text-align: justify;
                color: #000;
            }}
            
            /* Cabeçalho do documento */
            .header {{
                text-align: center;
                margin-bottom: 24pt;
                font-weight: bold;
            }}
            
            .header-forum {{
                font-size: 13pt;
                font-weight: bold;
                text-transform: uppercase;
                margin-bottom: 6pt;
            }}
            
            .header-vara {{
                font-size: 12pt;
                margin-bottom: 12pt;
            }}
            
            /* Títulos principais */
            h1 {{
                font-size: 14pt;
                font-weight: bold;
                text-align: center;
                text-transform: uppercase;
                letter-spacing: 1pt;
                margin: 24pt 0;
                padding: 12pt 0;
            }}
            
            h2 {{
                font-size: 13pt;
                font-weight: bold;
                text-transform: uppercase;
                margin: 24pt 0 12pt 0;
            }}
            
            h3 {{
                font-size: 12pt;
                font-weight: bold;
                margin: 18pt 0 10pt 0;
            }}
            
            h4 {{
                font-size: 12pt;
                font-weight: bold;
                font-style: italic;
                margin: 12pt 0 8pt 0;
            }}
            
            /* Parágrafos */
            p {{
                margin: 0 0 12pt 0;
                text-indent: 2.5cm;
                text-align: justify;
            }}
            
            /* Primeiro parágrafo após título sem recuo */
            h1 + p, h2 + p, h3 + p, h4 + p {{
                text-indent: 0;
            }}
            
            /* Seções numeradas (I -, II -, etc.) */
            .section-title {{
                font-weight: bold;
                text-indent: 0 !important;
                margin-top: 24pt;
                margin-bottom: 12pt;
            }}
            
            /* Qualificação das partes */
            .party-name {{
                font-weight: bold;
                text-transform: uppercase;
            }}
            
            .party-qualification {{
                text-indent: 0;
                margin-bottom: 6pt;
            }}
            
            /* Listas */
            ul, ol {{
                margin: 12pt 0 12pt 1cm;
                padding-left: 1cm;
            }}
            
            li {{
                margin-bottom: 8pt;
                text-align: justify;
            }}
            
            /* Lista com letras */
            ol.letters {{
                list-style-type: lower-alpha;
            }}
            
            /* Tabelas */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 18pt 0;
                font-size: 11pt;
            }}
            
            th, td {{
                border: 1px solid #333;
                padding: 8pt 10pt;
                text-align: left;
                vertical-align: top;
            }}
            
            th {{
                background-color: #f5f5f5;
                font-weight: bold;
            }}
            
            /* Formatação de texto */
            strong, b {{
                font-weight: bold;
            }}
            
            em, i {{
                font-style: italic;
            }}
            
            u {{
                text-decoration: underline;
            }}
            
            /* Citações */
            blockquote {{
                margin: 18pt 2cm 18pt 4cm;
                font-size: 11pt;
                font-style: italic;
                text-indent: 0;
                line-height: 1.5;
            }}
            
            /* Valor da causa */
            .valor-causa {{
                text-indent: 0;
                margin: 24pt 0;
            }}
            
            /* Bloco de assinatura */
            .signature-block {{
                margin-top: 48pt;
                text-align: center;
                page-break-inside: avoid;
            }}
            
            .signature-city-date {{
                text-align: right;
                margin-bottom: 48pt;
            }}
            
            .signature-line {{
                border-top: 1px solid #000;
                width: 250pt;
                margin: 0 auto;
                padding-top: 8pt;
            }}
            
            .signature-name {{
                font-weight: bold;
            }}
            
            .signature-oab {{
                font-size: 11pt;
            }}
            
            /* Termos em destaque */
            .termo-juridico {{
                font-style: italic;
            }}
            
            /* Separador horizontal */
            hr {{
                border: none;
                border-top: 1px solid #ccc;
                margin: 24pt 0;
            }}
            
            /* Rodapé */
            #footerContent {{
                font-size: 10pt;
                text-align: center;
                color: #666;
                font-family: Arial, sans-serif;
            }}
            
            /* Evitar quebras indesejadas */
            .no-break {{
                page-break-inside: avoid;
            }}
            
            /* Pedidos */
            .pedidos {{
                text-indent: 0;
            }}
            
            .pedidos li {{
                margin-bottom: 12pt;
            }}
        </style>
    </head>
    <body>
        {clean_html}
        <div id="footerContent">
            Página <pdf:pagenumber /> de <pdf:pagecount />
        </div>
    </body>
    </html>
    """

    # Gera o PDF
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(src=html_template, dest=buffer, encoding="UTF-8")

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
        plain_text = re.sub("<[^<]+?>", "", text)

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
    ptype = template.petition_type.name if template.petition_type else ""
    if ptype:
        return f"{template.name} · {ptype} ({scope})"
    return f"{template.name} ({scope})"


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

    return jsonify(
        {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "description": template.description,
            "defaults": defaults,
        }
    )


@bp.route("/civil/templates-partial")
@login_required
def civil_templates_partial():
    """HTMX partial: returns templates list for civil petitions."""
    templates = _accessible_templates_for(current_user, category="civel")
    return render_template(
        "petitions/partials/templates_list.html",
        templates=templates,
        category="civel",
    )


@bp.route("/family/templates-partial")
@login_required
def family_templates_partial():
    """HTMX partial: returns templates list for family petitions."""
    templates = _accessible_templates_for(current_user, category="familia")
    return render_template(
        "petitions/partials/templates_list.html",
        templates=templates,
        category="familia",
    )


@bp.route("/civil", methods=["GET", "POST"])
@login_required
@subscription_required
def civil_petitions():
    ensure_default_templates()
    form = CivilPetitionForm()

    templates = _accessible_templates_for(current_user, category="civel")
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

    # Preencher dados do advogado automaticamente
    if not form.is_submitted():
        form.advogado_nome.data = current_user.full_name or current_user.username
        form.advogado_oab.data = current_user.oab_number or ""

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

        # Usar dados do advogado logado (ignorar valores do form para segurança)
        advogado_nome = current_user.full_name or current_user.username
        advogado_oab = current_user.oab_number or "OAB não cadastrada"
        
        # Formatar data de assinatura
        data_assinatura = form.data_assinatura.data
        if data_assinatura:
            data_assinatura_str = data_assinatura.strftime("%d de %B de %Y").replace(
                "January", "janeiro"
            ).replace("February", "fevereiro").replace("March", "março").replace(
                "April", "abril"
            ).replace("May", "maio").replace("June", "junho").replace(
                "July", "julho"
            ).replace("August", "agosto").replace("September", "setembro").replace(
                "October", "outubro"
            ).replace("November", "novembro").replace("December", "dezembro")
        else:
            from datetime import date
            data_assinatura_str = date.today().strftime("%d de %B de %Y")

        context = {
            "forum": form.forum.data or "EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO",
            "vara": form.vara.data or "Vara de Família e Sucessões",
            "process_number": form.process_number.data,
            "action_type": form.action_type.data or "AÇÃO DE DIVÓRCIO C/C GUARDA E ALIMENTOS",
            # Dados do casamento
            "marriage_date": form.marriage_date.data
            if form.marriage_date.data
            else None,
            "marriage_city": form.marriage_city.data,
            "marriage_regime": form.marriage_regime.data,
            "separation_date": form.separation_date.data
            if form.separation_date.data
            else None,
            "prenup_summary": form.prenup_details.data
            if form.has_prenup.data
            else None,
            # Partes
            "spouse_one_name": form.spouse_one_name.data,
            "spouse_one_qualification": form.spouse_one_qualification.data,
            "author_address": form.author_address.data,
            "author_cpf": form.author_cpf.data,
            "spouse_two_name": form.spouse_two_name.data,
            "spouse_two_qualification": form.spouse_two_qualification.data,
            "defendant_address": form.defendant_address.data,
            # Filhos e pensão
            "children_info": form.children_info.data,
            "children_names": form.children_names.data,
            "custody_plan": form.custody_plan.data,
            "alimony_plan": form.alimony_plan.data,
            "defendant_income": form.defendant_income.data,
            "alimony_amount": form.alimony_amount.data,
            "health_plan_details": form.health_plan_details.data,
            # Patrimônio e dívidas
            "property_description": form.property_description.data,
            "debts_description": form.debts_description.data,
            # Violência doméstica
            "has_domestic_violence": form.has_domestic_violence.data,
            "domestic_violence_facts": form.domestic_violence_facts.data,
            "has_protective_order": form.has_protective_order.data,
            "protective_order_details": form.protective_order_details.data,
            "moral_damages_amount": form.moral_damages_amount.data,
            # Conteúdo
            "divorce_facts": form.divorce_facts.data,
            "facts": form.facts.data,
            "fundamentos": form.fundamentos.data,
            "pedidos": form.pedidos.data,
            "valor_causa": form.valor_causa.data,
            # Assinatura
            "cidade": form.cidade.data or "Local",
            "data_assinatura": data_assinatura_str,
            "advogado_nome": advogado_nome,
            "advogado_oab": advogado_oab,
            "lawyer_address": form.lawyer_address.data,
            "name_change": form.name_change.data,
            "request_free_justice": form.request_free_justice.data,
            "signature_author": form.signature_author.data,
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


@bp.route("/simple", methods=["GET", "POST"])
@login_required
@subscription_required
def simple_petitions():
    """Rota para petições simples (juntada de documentos, MLE, etc.)"""
    ensure_default_templates()
    form = SimplePetitionForm()

    # Buscar templates de petições simples (categoria civel, mas tipos específicos)
    templates = _accessible_templates_for(current_user, category="civel")
    # Filtrar para mostrar apenas modelos de petições simples
    simple_slugs = ['modelo-juntada-mle', 'modelo-juntada-documento', 'penhora-beneficio-inss']
    simple_templates = [t for t in templates if t.slug in simple_slugs or 'juntada' in t.slug.lower() or 'mle' in t.slug.lower() or 'penhora' in t.slug.lower()]
    
    # Se não houver templates específicos, usar todos os cíveis
    if not simple_templates:
        simple_templates = templates
    
    form.template_id.choices = [
        (template.id, _build_template_label(template)) for template in simple_templates
    ]

    if not form.template_id.choices:
        flash(
            "Nenhum modelo disponível. Entre em contato com o suporte.",
            "warning",
        )
        return redirect(url_for("petitions.personal_templates"))

    if not form.template_id.data and not form.is_submitted():
        form.template_id.data = form.template_id.choices[0][0]

    # Preencher dados do advogado automaticamente
    if not form.is_submitted():
        form.advogado_nome.data = current_user.full_name or current_user.username
        form.advogado_oab.data = current_user.oab_number or ""
        form.titular_conta.data = current_user.full_name or current_user.username

    if form.validate_on_submit():
        template = next(
            (tpl for tpl in simple_templates if tpl.id == form.template_id.data), None
        )

        if not template:
            flash("Modelo selecionado não foi encontrado.", "error")
            return redirect(request.url)

        try:
            attachments = _extract_attachments(form.documents.data)
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(request.url)

        # Usar dados do advogado logado
        advogado_nome = current_user.full_name or current_user.username
        advogado_oab = current_user.oab_number or "OAB não cadastrada"
        
        # Formatar data de assinatura
        data_assinatura = form.data_assinatura.data
        if data_assinatura:
            meses = {
                1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
                5: "maio", 6: "junho", 7: "julho", 8: "agosto",
                9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
            }
            data_assinatura_str = f"{data_assinatura.day} de {meses[data_assinatura.month]} de {data_assinatura.year}"
        else:
            from datetime import date
            hoje = date.today()
            meses = {
                1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
                5: "maio", 6: "junho", 7: "julho", 8: "agosto",
                9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
            }
            data_assinatura_str = f"{hoje.day} de {meses[hoje.month]} de {hoje.year}"

        context = {
            "forum": form.forum.data or "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO",
            "vara": form.vara.data or "Vara do Juizado Especial Cível",
            "process_number": form.process_number.data,
            "action_type": form.action_type.data or "AÇÃO",
            "author_name": form.author_name.data,
            "defendant_name": form.defendant_name.data or "",
            # Dados do MLE
            "valor_levantamento": form.valor_levantamento.data or "",
            "valor_extenso": form.valor_extenso.data or "",
            "folhas_referencia": form.folhas_referencia.data or "",
            "pix_chave": form.pix_chave.data or "",
            "banco_dados": form.banco_dados.data or "",
            "titular_conta": form.titular_conta.data or advogado_nome,
            "procuracao_folha": form.procuracao_folha.data or "",
            # Dados da Penhora INSS
            "valor_beneficio_inss": form.valor_beneficio_inss.data or "",
            "valor_beneficio_extenso": form.valor_beneficio_extenso.data or "",
            "percentual_penhora": form.percentual_penhora.data or "30%",
            "valor_penhora": form.valor_penhora.data or "",
            "valor_penhora_extenso": form.valor_penhora_extenso.data or "",
            "debito_atualizado": form.debito_atualizado.data or "",
            "debito_extenso": form.debito_extenso.data or "",
            "qtd_parcelas": form.qtd_parcelas.data or "",
            "tempo_inadimplencia": form.tempo_inadimplencia.data or "",
            # Conteúdo
            "facts": form.facts.data or "",
            "pedidos": form.pedidos.data or "",
            # Assinatura
            "cidade": form.cidade.data or "São Paulo",
            "data_assinatura_formatada": data_assinatura_str,
            "data_assinatura": data_assinatura_str,
            "advogado_nome": advogado_nome,
            "advogado_oab": advogado_oab,
        }

        rendered_text = render_template_string(template.content, **context)
        document_title = f"Peticao-Simples-{template.slug}"
        pdf_buffer = _render_pdf(rendered_text, document_title)
        base_filename = f"{template.slug}-{datetime.now().strftime('%Y%m%d-%H%M')}"
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
        "petitions/simple/form.html",
        title="Petições Simples",
        form=form,
        templates=simple_templates,
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
