import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from functools import wraps
from io import BytesIO
from zipfile import ZipFile

import bleach
from flask import (
    abort,
    current_app,
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

from app import db, limiter
from app.billing.decorators import subscription_required
from app.billing.utils import (
    BillingAccessError,
    ensure_petition_type,
    record_petition_usage,
    slugify,
)
from app.decorators import validate_with_schema
from app.models import (
    PetitionAttachment,
    PetitionModel,
    PetitionModelSection,
    PetitionSection,
    PetitionType,
    SavedPetition,
)
from app.petitions import bp
from app.petitions.forms import (
    CivilPetitionForm,
    FamilyPetitionForm,
    SimplePetitionForm,
)
from app.rate_limits import ADMIN_API_LIMIT
from app.schemas import (
    AttachmentUploadSchema,
    GenerateDynamicSchema,
    GenerateModelSchema,
    PetitionSaveSchema,
)
from app.utils.error_messages import format_error_for_user
from app.services.pdf_converter import convert_to_pdf, CONVERTIBLE_EXTENSIONS

# Extensões permitidas - agora incluindo mais formatos que podem ser convertidos
ATTACHMENT_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "gif", "txt", "xls", "xlsx"}
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 MB por arquivo
MAX_ATTACHMENT_COUNT = None  # Ilimitado
MAX_TOTAL_SIZE_PER_PETITION = 50 * 1024 * 1024  # 50 MB total por petição


def require_active_user(f):
    """Decorator para validar se usuário não foi anonimizado ou deletado"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.billing_status == "anonymized":
            # Verificar se tem uma solicitação de deanonimização em andamento
            from app.models import DeanonymizationRequest

            pending_deanon = DeanonymizationRequest.query.filter_by(
                user_id=current_user.id, status="pending"
            ).first()

            if pending_deanon:
                return (
                    jsonify(
                        {
                            "error": "Sua solicitação de deanonimização está em análise. "
                            "Assim que for aprovada, poderá gerar petições novamente."
                        }
                    ),
                    403,
                )
            else:
                return (
                    jsonify(
                        {
                            "error": "Usuários anonimizados não podem gerar petições. "
                            "Os dados originais foram substituídos por identificadores anônimos. "
                            "Solicite a restauração da conta antes de continuar."
                        }
                    ),
                    403,
                )
        elif current_user.billing_status == "deleted" or not current_user.is_active:
            return (
                jsonify(
                    {
                        "error": "Sua conta foi desativada ou deletada. "
                        "Não é possível gerar petições com esta conta."
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated_function


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


def _extract_attachments(files, convert_to_pdf_enabled=True):
    """
    Extrai e processa anexos, convertendo para PDF quando possível.
    
    Args:
        files: Lista de arquivos do request
        convert_to_pdf_enabled: Se True, converte arquivos para PDF
        
    Returns:
        list: Lista de dicionários com filename e data
    """
    attachments = []
    if not files:
        return attachments

    total_size = 0
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
            raise ValueError(
                f"{filename} excede o limite de {MAX_ATTACHMENT_SIZE // (1024 * 1024)} MB por arquivo."
            )

        if total_size + size > MAX_TOTAL_SIZE_PER_PETITION:
            raise ValueError(f"Total de arquivos excede o limite de 50 MB por petição.")

        # Ler dados do arquivo
        file_data = file_storage.read()
        
        # Converter para PDF se habilitado e não for PDF
        if convert_to_pdf_enabled and ext != "pdf":
            try:
                converted_data, new_filename = convert_to_pdf(file_data, filename)
                # Verificar se conversão foi bem sucedida (arquivo mudou para .pdf)
                if new_filename.endswith('.pdf'):
                    current_app.logger.info(f"Arquivo {filename} convertido para {new_filename}")
                    file_data = converted_data
                    filename = new_filename
            except Exception as e:
                current_app.logger.warning(f"Falha ao converter {filename} para PDF: {e}")
                # Mantém arquivo original se conversão falhar
        
        attachments.append({"filename": filename, "data": file_data})
        total_size += len(file_data)

    return attachments


# =============================================================================
# ROTAS PARA FORMULÁRIO DINÂMICO
# =============================================================================


# =============================================================================
# ROTAS PARA FORMULÁRIO DINÂMICO
# =============================================================================


@bp.route("/dynamic/<slug>")
@login_required
@subscription_required
def dynamic_form(slug):
    """Renderiza o formulário dinâmico baseado nas seções do modelo de petição."""

    # Buscar tipo de petição
    petition_type = PetitionType.query.filter_by(slug=slug).first_or_404()

    # Verificar se usa formulário dinâmico
    if not petition_type.use_dynamic_form:
        # Redirecionar para formulário tradicional se não for dinâmico
        flash(
            "Este tipo de petição não está configurado para formulário dinâmico.",
            "warning",
        )
        return redirect(url_for("main.peticionador"))

    # Buscar modelo padrão para este tipo de petição
    petition_model = PetitionModel.query.filter_by(
        petition_type_id=petition_type.id, is_active=True
    ).first()

    if not petition_model:
        flash(
            "Nenhum modelo ativo encontrado para este tipo de petição.",
            "warning",
        )
        return redirect(url_for("main.peticionador"))

    # Verificar se está editando uma petição existente
    edit_id = request.args.get("edit_id", type=int)
    edit_petition = None

    if edit_id:
        edit_petition = SavedPetition.query.filter_by(
            id=edit_id, user_id=current_user.id, petition_type_id=petition_type.id
        ).first()

        if edit_petition and edit_petition.status == "cancelled":
            flash("Petições canceladas não podem ser editadas.", "warning")
            edit_petition = None

    # Buscar seções configuradas para o modelo
    sections_config = petition_model.get_sections_ordered()

    # Coletar IDs de seções vinculadas com a seção pai (linked_section_id -> parent_section_id)
    linked_sections_map = {}  # {linked_section_id: parent_section_id}

    # Montar estrutura para o template
    sections = []
    for config in sections_config:
        section = config.section
        if section and section.is_active:
            # Verificar se algum campo tem seção vinculada
            for field in section.fields_schema or []:
                if field.get("linked_section_id"):
                    linked_sections_map[field.get("linked_section_id")] = section.id

            sections.append(
                {
                    "section": {
                        "id": section.id,
                        "name": section.name,
                        "slug": section.slug,
                        "description": section.description,
                        "icon": section.icon,
                        "color": section.color,
                        "fields_schema": section.fields_schema or [],
                    },
                    "is_required": config.is_required,
                    "is_expanded": config.is_expanded,
                    "field_overrides": config.field_overrides or {},
                }
            )

    # Adicionar seções vinculadas LOGO APÓS a seção que as referencia
    sections_with_linked = []
    for section_data in sections:
        sections_with_linked.append(section_data)
        section_id = section_data["section"]["id"]
        
        # Verificar se alguma seção vinculada deve ser inserida após esta
        for linked_id, parent_id in linked_sections_map.items():
            if parent_id == section_id:
                # Verificar se a seção já está incluída
                if not any(s["section"]["id"] == linked_id for s in sections):
                    linked_section = PetitionSection.query.get(linked_id)
                    if linked_section and linked_section.is_active:
                        sections_with_linked.append(
                            {
                                "section": {
                                    "id": linked_section.id,
                                    "name": linked_section.name,
                                    "slug": linked_section.slug,
                                    "description": linked_section.description,
                                    "icon": linked_section.icon,
                                    "color": linked_section.color,
                                    "fields_schema": linked_section.fields_schema or [],
                                },
                                "is_required": False,  # Seções vinculadas não são obrigatórias por padrão
                                "is_expanded": False,  # Começa recolhida
                                "field_overrides": {},
                                "is_linked_section": True,  # Marcador para seções vinculadas
                                "linked_to_fields": [],  # Será preenchido pelo frontend
                            }
                        )

    sections = sections_with_linked

    # Serializar seções para JSON (para Alpine.js)
    sections_json = json.dumps(sections, ensure_ascii=False)

    # Serializar petição para edição (se existir)
    edit_petition_json = None
    locked_fields = []
    if edit_petition:
        # Obter campos bloqueados se a petição foi paga
        locked_fields = edit_petition.get_locked_fields()

        edit_petition_json = json.dumps(
            {
                "id": edit_petition.id,
                "form_data": edit_petition.form_data or {},
                "status": edit_petition.status,
                "title": edit_petition.title,
                "process_number": edit_petition.process_number,
                "is_paid": edit_petition.is_paid,
                "locked_fields": locked_fields,
            },
            ensure_ascii=False,
        )

    return render_template(
        "petitions/dynamic_form.html",
        petition_type=petition_type,
        petition_model=petition_model,
        sections=sections,
        sections_json=sections_json,
        edit_petition=edit_petition,
        edit_petition_json=edit_petition_json,
        locked_fields=locked_fields,
    )


@bp.route("/generate-dynamic", methods=["POST"])
@login_required
@subscription_required
@limiter.limit("10 per minute")
@validate_with_schema(GenerateDynamicSchema, location="json")
@require_active_user
def generate_dynamic():
    """Gera a petição a partir dos dados do formulário dinâmico."""
    try:
        data = request.validated_data
        petition_model_id = data.get("petition_model_id")
        form_data = data.get("form_data", {})
        with_ai = data.get("with_ai", False)

        # Buscar modelo de petição
        petition_model = PetitionModel.query.get_or_404(petition_model_id)
        petition_type = petition_model.petition_type

        # Verificar se há template Jinja2 definido
        if petition_model.template_content and petition_model.template_content.strip():
            # Usar template Jinja2
            try:
                from jinja2 import Template

                template = Template(petition_model.template_content)
                rendered_content = template.render(**form_data)

                # Gerar PDF com o conteúdo renderizado
                pdf_buffer = BytesIO()
                html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {{ margin: 2.5cm 3cm; }}
                    body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.5; text-align: justify; }}
                    h1, h2, h3 {{ font-family: Arial, sans-serif; }}
                    h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                    h2 {{ font-size: 12pt; margin-top: 18pt; }}
                    p {{ text-indent: 2cm; margin-bottom: 12pt; }}
                    .header {{ text-align: center; margin-bottom: 24pt; }}
                    .signature {{ margin-top: 48pt; text-align: center; }}
                </style>
            </head>
            <body>
                <pre style="font-family: 'Times New Roman', serif; white-space: pre-wrap;">{rendered_content}</pre>
            </body>
            </html>
            """

                pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

                if pisa_status.err:
                    return jsonify({"error": "Erro ao gerar PDF"}), 500

                pdf_buffer.seek(0)

                # Registrar uso
                try:
                    record_petition_usage(current_user, petition_type)
                except BillingAccessError as e:
                    return jsonify({"error": str(e)}), 403

                filename = f"{petition_type.slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                return send_file(
                    pdf_buffer,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=filename,
                )

            except Exception as e:
                current_app.logger.error(
                    f"Erro ao renderizar template Jinja2: {str(e)}"
                )
                # Fallback para geração dinâmica
                return _generate_dynamic_fallback(
                    petition_model, petition_type, form_data
                )

        else:
            # Usar geração dinâmica tradicional
            return _generate_dynamic_fallback(petition_model, petition_type, form_data)

    except Exception as e:
        error_msg = format_error_for_user(e, "Erro ao gerar petição dinâmica")
        return jsonify({"error": error_msg}), 400


def _generate_dynamic_fallback(petition_model, petition_type, form_data):
    """Fallback para geração dinâmica tradicional quando não há template Jinja2"""

    # Buscar seções configuradas para o modelo
    sections_config = petition_model.get_sections_ordered()

    # Gerar conteúdo HTML baseado nas seções e campos preenchidos
    template_content = f"<h1>{petition_type.name}</h1>\n\n"

    for config in sections_config:
        section = db.session.get(PetitionSection, config.section_id)
        if section and section.is_active and section.fields_schema:
            # Adicionar cabeçalho da seção
            template_content += f"<h2>{section.name}</h2>\n"

            # Garantir que fields_schema é uma lista
            fields_list = (
                section.fields_schema if isinstance(section.fields_schema, list) else []
            )

            for field in fields_list:
                if not isinstance(field, dict):
                    continue
                field_name = f"{section.slug}_{field.get('name', '')}"
                field_value = form_data.get(field_name, "").strip()

                if field_value:  # Só incluir campos preenchidos
                    field_label = field.get(
                        "label", field.get("name", "").replace("_", " ").title()
                    )
                    field_type = field.get("type", "text")

                    # Formatar o conteúdo baseado no tipo de campo
                    if field_type == "editor":
                        # Para campos de editor, o conteúdo já vem em HTML
                        template_content += f"<div>{field_value}</div>\n\n"
                    elif field_type == "textarea":
                        # Para textarea, converter quebras de linha em parágrafos
                        paragraphs = field_value.split("\n\n")
                        for para in paragraphs:
                            if para.strip():
                                template_content += f"<p>{para.strip()}</p>\n"
                        template_content += "\n"
                    else:
                        # Para outros campos, mostrar como parágrafo simples
                        template_content += (
                            f"<p><strong>{field_label}:</strong> {field_value}</p>\n"
                        )

    # Se não há conteúdo das seções, mostrar mensagem padrão
    if template_content == f"<h1>{petition_type.name}</h1>\n\n":
        template_content += f"""
        <p><strong>Autor:</strong> {form_data.get("author_name", "Não informado")}</p>
        <p><strong>Valor da Causa:</strong> R$ {form_data.get("valor_causa", "0,00")}</p>
        <p><strong>Fórum:</strong> {form_data.get("forum", "Não informado")}</p>
        <p><strong>Vara:</strong> {form_data.get("vara", "Não informado")}</p>
        """

    # Gerar PDF
    try:
        pdf_buffer = BytesIO()
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ margin: 2.5cm 3cm; }}
                body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.5; text-align: justify; }}
                h1, h2, h3 {{ font-family: Arial, sans-serif; }}
                h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                h2 {{ font-size: 12pt; margin-top: 18pt; }}
                p {{ text-indent: 2cm; margin-bottom: 12pt; }}
                .header {{ text-align: center; margin-bottom: 24pt; }}
                .signature {{ margin-top: 48pt; text-align: center; }}
            </style>
        </head>
        <body>
            {template_content}
        </body>
        </html>
        """

        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

        if pisa_status.err:
            return jsonify({"error": "Erro ao gerar PDF"}), 500

        pdf_buffer.seek(0)

        # Registrar uso
        try:
            record_petition_usage(current_user, petition_type)
        except BillingAccessError as e:
            return jsonify({"error": str(e)}), 403

        filename = (
            f"{petition_type.slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500


@bp.route("/model/<slug>")
@login_required
@subscription_required
def model_form(slug):
    """Renderiza o formulário baseado em um modelo de petição."""

    # Buscar modelo de petição
    petition_model = PetitionModel.query.filter_by(
        slug=slug, is_active=True
    ).first_or_404()

    # Verificar se está editando uma petição existente
    edit_id = request.args.get("edit_id", type=int)
    edit_petition = None

    if edit_id:
        edit_petition = SavedPetition.query.filter_by(
            id=edit_id, user_id=current_user.id, petition_model_id=petition_model.id
        ).first()

        if edit_petition and edit_petition.status == "cancelled":
            flash("Petições canceladas não podem ser editadas.", "warning")
            edit_petition = None

    # Buscar seções do modelo
    sections_config = petition_model.get_sections_ordered()

    # Montar estrutura para o template
    sections = []
    for config in sections_config:
        section = config.section
        if section and section.is_active:
            sections.append(
                {
                    "section": {
                        "id": section.id,
                        "name": section.name,
                        "slug": section.slug,
                        "description": section.description,
                        "icon": section.icon,
                        "color": section.color,
                        "fields_schema": section.fields_schema or [],
                    },
                    "is_required": config.is_required,
                    "is_expanded": config.is_expanded,
                    "field_overrides": config.field_overrides or {},
                }
            )

    # Serializar seções para JSON (para Alpine.js)
    sections_json = json.dumps(sections, ensure_ascii=False)

    # Serializar petição para edição (se existir)
    edit_petition_json = None
    if edit_petition:
        edit_petition_json = json.dumps(
            {
                "id": edit_petition.id,
                "form_data": edit_petition.form_data or {},
                "status": edit_petition.status,
                "title": edit_petition.title,
                "process_number": edit_petition.process_number,
            },
            ensure_ascii=False,
        )

    return render_template(
        "petitions/model_form.html",
        petition_model=petition_model,
        sections=sections,
        sections_json=sections_json,
        edit_petition=edit_petition,
        edit_petition_json=edit_petition_json,
    )


@bp.route("/generate-model", methods=["POST"])
@login_required
@subscription_required
@limiter.limit("10 per minute")
@validate_with_schema(GenerateModelSchema, location="json")
@require_active_user
def generate_model():
    """Gera a petição a partir dos dados do formulário baseado em modelo."""
    try:
        data = request.validated_data
        petition_model_id = data.get("petition_model_id")
        form_data = data.get("form_data", {})

        # Buscar modelo de petição
        petition_model = PetitionModel.query.get_or_404(petition_model_id)

        # Verificar se o modelo tem template
        if not petition_model.template_content:
            return jsonify({"error": "Modelo não possui template configurado"}), 400

        # Renderizar template do modelo
        try:
            template_content = render_template_string(
                petition_model.template_content, **form_data
            )
        except Exception as e:
            return jsonify(
                {"error": f"Erro ao renderizar template do modelo: {str(e)}"}
            ), 500

        # Gerar PDF
        try:
            pdf_buffer = BytesIO()
            html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ margin: 2.5cm 3cm; }}
                body {{ font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.5; text-align: justify; }}
                h1, h2, h3 {{ font-family: Arial, sans-serif; }}
                h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                h2 {{ font-size: 12pt; margin-top: 18pt; }}
                p {{ text-indent: 2cm; margin-bottom: 12pt; }}
                .header {{ text-align: center; margin-bottom: 24pt; }}
                .signature {{ margin-top: 48pt; text-align: center; }}
            </style>
        </head>
        <body>
            {template_content}
        </body>
        </html>
        """

            pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)

            if pisa_status.err:
                return jsonify({"error": "Erro ao gerar PDF"}), 500

            pdf_buffer.seek(0)

            # Registrar uso (usando o petition_type associado ao modelo)
            try:
                if petition_model.petition_type:
                    record_petition_usage(current_user, petition_model.petition_type)
            except BillingAccessError as e:
                return jsonify({"error": str(e)}), 403

            filename = (
                f"{petition_model.slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

            return send_file(
                pdf_buffer,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=filename,
            )

        except Exception as e:
            return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500

    except Exception as e:
        error_msg = format_error_for_user(e, "Erro ao gerar petição a partir de modelo")
        return jsonify({"error": error_msg}), 400


# ============================================================================
# ROTAS PARA PETIÇÕES SALVAS (CRUD)
# ============================================================================


@bp.route("/saved")
@login_required
def saved_list():
    """Lista todas as petições salvas do usuário."""
    from app.utils.pagination import PaginationHelper

    # Filtros
    status_filter = request.args.get("status", "all")
    search = request.args.get("search", "").strip()
    per_page = 20

    # Query base
    query = SavedPetition.query.filter_by(user_id=current_user.id)

    # Filtro de status
    if status_filter != "all":
        query = query.filter_by(status=status_filter)

    # Busca por número de processo, título ou partes
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SavedPetition.process_number.ilike(search_term),
                SavedPetition.title.ilike(search_term),
                SavedPetition.form_data["autor_nome"].astext.ilike(search_term),
                SavedPetition.form_data["reu_nome"].astext.ilike(search_term),
            )
        )

    # Ordenar por mais recentes
    query = query.order_by(SavedPetition.updated_at.desc())

    # Paginação Universal
    pagination = PaginationHelper(
        query=query,
        per_page=per_page,
        filters={'status': status_filter, 'search': search}
    )
    petitions = pagination.items

    # Estatísticas
    stats = {
        "total": SavedPetition.query.filter_by(user_id=current_user.id).count(),
        "draft": SavedPetition.query.filter_by(
            user_id=current_user.id, status="draft"
        ).count(),
        "completed": SavedPetition.query.filter_by(
            user_id=current_user.id, status="completed"
        ).count(),
        "cancelled": SavedPetition.query.filter_by(
            user_id=current_user.id, status="cancelled"
        ).count(),
    }

    return render_template(
        "petitions/saved_list.html",
        title="Minhas Petições",
        petitions=petitions,
        pagination=pagination,
        stats=stats,
        status_filter=status_filter,
        search=search,
    )


@bp.route("/saved/<int:petition_id>")
@login_required
def saved_view(petition_id):
    """Visualiza detalhes de uma petição salva."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    return render_template(
        "petitions/saved_view.html",
        title=petition.title or f"Petição #{petition.id}",
        petition=petition,
    )


@bp.route("/saved/<int:petition_id>/edit")
@login_required
def saved_edit(petition_id):
    """Redireciona para edição da petição."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    if petition.status == "cancelled":
        flash("Petições canceladas não podem ser editadas.", "warning")
        return redirect(url_for("petitions.saved_list"))

    # Redirecionar para o formulário dinâmico com os dados carregados
    return redirect(
        url_for(
            "petitions.dynamic_form",
            slug=petition.petition_type.slug,
            edit_id=petition.id,
        )
    )


@bp.route("/api/save", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
@validate_with_schema(PetitionSaveSchema, location="json")
@require_active_user
def api_save_petition():
    """API para salvar uma petição (novo ou atualização)."""
    try:
        data = request.validated_data

        petition_type_id = data.get("petition_type_id")
        petition_model_id = data.get("petition_model_id")
        form_data = data.get("data", {})
        title = data.get("title")
        notes = data.get("notes")

        # Verificar se é edição ou novo
        if petition_id:
            petition = SavedPetition.query.filter_by(
                id=petition_id, user_id=current_user.id
            ).first()

            if not petition:
                return jsonify(
                    {"success": False, "error": "Petição não encontrada"}
                ), 404

            if petition.status == "cancelled":
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Petição cancelada não pode ser editada",
                        }
                    ),
                    400,
                )
        else:
            # Criar nova petição
            petition = SavedPetition(
                user_id=current_user.id,
                petition_type_id=petition_type_id,
                petition_model_id=petition_model_id,
            )
            db.session.add(petition)

        # Atualizar dados
        petition.form_data = form_data
        petition.process_number = form_data.get("processo_numero") or form_data.get(
            "processo_number"
        )

        # Ações
        if action == "complete":
            petition.status = "completed"
            petition.completed_at = datetime.now(timezone.utc)
        elif action == "cancel":
            petition.status = "cancelled"
            petition.cancelled_at = datetime.now(timezone.utc)
        else:
            if petition.status != "completed":
                petition.status = "draft"

        try:
            db.session.commit()

            # Gerar título automático após commit (para ter o ID)
            if not petition.title:  # Só gerar se não tiver título
                autor = form_data.get("autor_nome", "").strip()
                reu = form_data.get("reu_nome", "").strip()

                if petition_model_id:
                    petition_model = db.session.get(PetitionModel, petition_model_id)
                    base_name = (
                        petition_model.name if petition_model else "Modelo de Petição"
                    )
                else:
                    petition_type = db.session.get(PetitionType, petition_type_id)
                    base_name = petition_type.name if petition_type else "Petição"

                if autor and reu:
                    petition.title = f"{base_name} - {autor} x {reu}"
                elif autor:
                    petition.title = f"{base_name} - {autor}"
                else:
                    petition.title = f"{base_name} - #{petition.id}"

            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "petition_id": petition.id,
                    "message": "Petição salva com sucesso!",
                    "status": petition.status,
                }
            )
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        error_msg = format_error_for_user(e, "Erro ao salvar petição")
        return jsonify({"success": False, "error": error_msg}), 400


@bp.route("/api/saved/<int:petition_id>/cancel", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def api_cancel_petition(petition_id):
    """API para cancelar uma petição."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    if petition.status == "cancelled":
        return jsonify({"success": False, "error": "Petição já está cancelada"}), 400

    petition.status = "cancelled"
    petition.cancelled_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Petição cancelada com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/saved/<int:petition_id>/restore", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def api_restore_petition(petition_id):
    """API para restaurar uma petição cancelada."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    if petition.status != "cancelled":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Apenas petições canceladas podem ser restauradas",
                }
            ),
            400,
        )

    petition.status = "draft"
    petition.cancelled_at = None

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Petição restaurada com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/saved/<int:petition_id>/delete", methods=["DELETE"])
@login_required
def api_delete_petition(petition_id):
    """API para excluir permanentemente uma petição."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    try:
        # Primeiro remove os anexos físicos
        for attachment in petition.attachments:
            try:
                import os

                file_path = os.path.join(
                    current_app.config.get("UPLOAD_FOLDER", "uploads"),
                    "attachments",
                    attachment.stored_filename,
                )
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass

        db.session.delete(petition)
        db.session.commit()
        return jsonify(
            {"success": True, "message": "Petição excluída permanentemente!"}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# ROTAS PARA ANEXOS/PROVAS
# ============================================================================

ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "txt",
    "xls",
    "xlsx",
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/api/saved/<int:petition_id>/attachments", methods=["GET"])
@login_required
def api_list_attachments(petition_id):
    """Lista anexos de uma petição."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    attachments = []
    for att in petition.attachments:
        attachments.append(
            {
                "id": att.id,
                "filename": att.filename,
                "file_type": att.file_type,
                "file_size": att.file_size,
                "file_size_display": att.get_file_size_display(),
                "category": att.category,
                "description": att.description,
                "icon": att.get_icon(),
                "uploaded_at": att.uploaded_at.isoformat() if att.uploaded_at else None,
            }
        )

    return jsonify(attachments)


@bp.route("/api/saved/<int:petition_id>/attachments", methods=["POST"])
@login_required
def api_upload_attachment(petition_id):
    """Upload de anexo para uma petição."""

    petition = SavedPetition.query.filter_by(
        id=petition_id, user_id=current_user.id
    ).first_or_404()

    if petition.status == "cancelled":
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Não é possível anexar arquivos a petições canceladas",
                }
            ),
            400,
        )

    if "file" not in request.files:
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "error": "Arquivo sem nome"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Tipo de arquivo não permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}",
                }
            ),
            400,
        )

    # Verificar tamanho
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_ATTACHMENT_SIZE:  # 20MB
        return jsonify(
            {
                "success": False,
                "error": f"Arquivo muito grande. Máximo: {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB por arquivo",
            }
        ), 400

    # Verificar tamanho total já enviado
    current_total = sum(att.file_size for att in petition.attachments)
    if current_total + file_size > MAX_TOTAL_SIZE_PER_PETITION:  # 50MB
        remaining = (MAX_TOTAL_SIZE_PER_PETITION - current_total) // (1024 * 1024)
        return jsonify(
            {
                "success": False,
                "error": f"Limite total de 50MB por petição excedido. Espaço disponível: {remaining}MB",
            }
        ), 400

    # Gerar nome único
    original_filename = secure_filename(file.filename)
    ext = (
        original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    )
    stored_filename = f"{uuid.uuid4().hex}.{ext}"

    # Criar diretório se não existir
    upload_dir = os.path.join(
        current_app.config.get("UPLOAD_FOLDER", "uploads"), "attachments"
    )
    os.makedirs(upload_dir, exist_ok=True)

    # Salvar arquivo
    file_path = os.path.join(upload_dir, stored_filename)
    file.save(file_path)

    # Criar registro no banco
    attachment = PetitionAttachment(
        saved_petition_id=petition.id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_type=file.content_type,
        file_size=file_size,
        category=request.form.get("category", "prova"),
        description=request.form.get("description", ""),
        uploaded_by_id=current_user.id,
    )

    db.session.add(attachment)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "attachment": {
                "id": attachment.id,
                "filename": attachment.filename,
                "file_size_display": attachment.get_file_size_display(),
                "icon": attachment.get_icon(),
            },
        }
    )


@bp.route("/api/attachments/<int:attachment_id>", methods=["DELETE"])
@login_required
def api_delete_attachment(attachment_id):
    """Exclui um anexo."""

    attachment = PetitionAttachment.query.get_or_404(attachment_id)

    # Verificar permissão
    if attachment.saved_petition.user_id != current_user.id:
        return jsonify({"success": False, "error": "Sem permissão"}), 403

    # Remover arquivo físico
    try:
        file_path = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "uploads"),
            "attachments",
            attachment.stored_filename,
        )
        if os.path.exists(file_path):
            os.remove(file_path)
    except:
        pass

    db.session.delete(attachment)
    db.session.commit()

    return jsonify({"success": True, "message": "Anexo removido!"})


@bp.route("/attachments/<int:attachment_id>/download")
@login_required
def download_attachment(attachment_id):
    """Download de um anexo."""

    attachment = PetitionAttachment.query.get_or_404(attachment_id)

    # Verificar permissão
    if attachment.saved_petition.user_id != current_user.id:
        abort(403)

    file_path = os.path.join(
        current_app.config.get("UPLOAD_FOLDER", "uploads"),
        "attachments",
        attachment.stored_filename,
    )

    if not os.path.exists(file_path):
        abort(404)

    return send_file(file_path, download_name=attachment.filename, as_attachment=True)
