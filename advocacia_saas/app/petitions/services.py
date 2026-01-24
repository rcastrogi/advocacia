"""
Petitions Services - Camada de lógica de negócios
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import bleach
from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa

from app import db
from app.models import PetitionModel, PetitionType, SavedPetition
from app.petitions.repository import (
    PetitionAttachmentRepository,
    PetitionModelRepository,
    PetitionSectionRepository,
    PetitionTypeRepository,
    SavedPetitionRepository,
)
from app.utils.pagination import PaginationHelper

# Constantes
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024  # 20 MB por arquivo
MAX_TOTAL_SIZE_PER_PETITION = 50 * 1024 * 1024  # 50 MB total por petição
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


class PetitionTypeService:
    """Serviço para tipos de petição"""

    @staticmethod
    def get_by_slug_or_404(slug: str) -> PetitionType:
        """Obtém tipo de petição ou levanta 404"""
        petition_type = PetitionTypeRepository.get_by_slug(slug)
        if not petition_type:
            from flask import abort

            abort(404)
        return petition_type


class PetitionModelService:
    """Serviço para modelos de petição"""

    @staticmethod
    def get_active_for_type(petition_type_id: int) -> PetitionModel | None:
        """Obtém modelo ativo para um tipo de petição"""
        return PetitionModelRepository.get_active_for_type(petition_type_id)

    @staticmethod
    def get_by_slug_or_404(slug: str) -> PetitionModel:
        """Obtém modelo pelo slug ou levanta 404"""
        model = PetitionModelRepository.get_by_slug(slug)
        if not model:
            from flask import abort

            abort(404)
        return model


class DynamicFormService:
    """Serviço para formulários dinâmicos"""

    @staticmethod
    def build_sections_data(petition_model: PetitionModel) -> tuple[list, str]:
        """Constrói dados de seções para o template"""
        sections_config = petition_model.get_sections_ordered()

        # Mapear seções vinculadas
        linked_sections_map = {}

        sections = []
        for config in sections_config:
            section = config.section
            if section and section.is_active:
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

        # Adicionar seções vinculadas
        sections_with_linked = []
        for section_data in sections:
            sections_with_linked.append(section_data)
            section_id = section_data["section"]["id"]

            for linked_id, parent_id in linked_sections_map.items():
                if parent_id == section_id:
                    if not any(s["section"]["id"] == linked_id for s in sections):
                        linked_section = PetitionSectionRepository.get_active_by_id(
                            linked_id
                        )
                        if linked_section:
                            sections_with_linked.append(
                                {
                                    "section": {
                                        "id": linked_section.id,
                                        "name": linked_section.name,
                                        "slug": linked_section.slug,
                                        "description": linked_section.description,
                                        "icon": linked_section.icon,
                                        "color": linked_section.color,
                                        "fields_schema": linked_section.fields_schema
                                        or [],
                                    },
                                    "is_required": False,
                                    "is_expanded": False,
                                    "field_overrides": {},
                                    "is_linked_section": True,
                                    "linked_to_fields": [],
                                }
                            )

        sections_json = json.dumps(sections_with_linked, ensure_ascii=False)
        return sections_with_linked, sections_json

    @staticmethod
    def build_edit_petition_data(
        petition: SavedPetition | None,
    ) -> tuple[str | None, list]:
        """Constrói dados de petição para edição"""
        if not petition:
            return None, []

        locked_fields = petition.get_locked_fields()
        edit_data = json.dumps(
            {
                "id": petition.id,
                "form_data": petition.form_data or {},
                "status": petition.status,
                "title": petition.title,
                "process_number": petition.process_number,
                "is_paid": petition.is_paid,
                "locked_fields": locked_fields,
            },
            ensure_ascii=False,
        )

        return edit_data, locked_fields


class PDFGenerationService:
    """Serviço para geração de PDF"""

    # Tags HTML permitidas
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

    @staticmethod
    def render_pdf_from_html(html_content: str, title: str) -> BytesIO:
        """Renderiza conteúdo HTML para PDF"""
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(src=html_content, dest=buffer, encoding="UTF-8")

        if pisa_status.err:
            # Fallback para texto simples
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

            plain_text = re.sub("<[^<]+?>", "", html_content)
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

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitiza HTML para PDF"""
        return bleach.clean(
            text,
            tags=PDFGenerationService.ALLOWED_TAGS,
            attributes=PDFGenerationService.ALLOWED_ATTRIBUTES,
            strip=True,
        )

    @staticmethod
    def generate_from_template(
        petition_model: PetitionModel,
        form_data: dict[str, Any],
    ) -> tuple[BytesIO | None, str | None]:
        """Gera PDF a partir de template Jinja2"""
        if (
            not petition_model.template_content
            or not petition_model.template_content.strip()
        ):
            return None, "Template não configurado"

        try:
            from jinja2 import Template

            template = Template(petition_model.template_content)
            rendered_content = template.render(**form_data)

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {{ margin: 2.5cm 3cm; }}
                    body {{ font-family: 'Times New Roman', serif; font-size: 12pt; 
                            line-height: 1.5; text-align: justify; }}
                    h1, h2, h3 {{ font-family: Arial, sans-serif; }}
                    h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                    h2 {{ font-size: 12pt; margin-top: 18pt; }}
                    p {{ text-indent: 2cm; margin-bottom: 12pt; }}
                </style>
            </head>
            <body>
                <pre style="font-family: 'Times New Roman', serif; white-space: pre-wrap;">
                    {rendered_content}
                </pre>
            </body>
            </html>
            """

            pdf_buffer = PDFGenerationService.render_pdf_from_html(
                html_content,
                petition_model.name,
            )
            return pdf_buffer, None

        except Exception as e:
            current_app.logger.error(f"Erro ao renderizar template: {str(e)}")
            return None, f"Erro ao renderizar template: {str(e)}"

    @staticmethod
    def generate_dynamic_fallback(
        petition_model: PetitionModel,
        petition_type: PetitionType,
        form_data: dict[str, Any],
    ) -> BytesIO:
        """Geração dinâmica quando não há template Jinja2"""
        sections_config = petition_model.get_sections_ordered()
        template_content = f"<h1>{petition_type.name}</h1>\n\n"

        for config in sections_config:
            section = PetitionSectionRepository.get_by_id(config.section_id)
            if section and section.is_active and section.fields_schema:
                template_content += f"<h2>{section.name}</h2>\n"

                fields_list = (
                    section.fields_schema
                    if isinstance(section.fields_schema, list)
                    else []
                )

                for field in fields_list:
                    if not isinstance(field, dict):
                        continue
                    field_name = f"{section.slug}_{field.get('name', '')}"
                    field_value = form_data.get(field_name, "").strip()

                    if field_value:
                        field_label = field.get(
                            "label", field.get("name", "").replace("_", " ").title()
                        )
                        field_type = field.get("type", "text")

                        if field_type == "editor":
                            template_content += f"<div>{field_value}</div>\n\n"
                        elif field_type == "textarea":
                            paragraphs = field_value.split("\n\n")
                            for para in paragraphs:
                                if para.strip():
                                    template_content += f"<p>{para.strip()}</p>\n"
                            template_content += "\n"
                        else:
                            template_content += f"<p><strong>{field_label}:</strong> {field_value}</p>\n"

        # Se não há conteúdo das seções
        if template_content == f"<h1>{petition_type.name}</h1>\n\n":
            template_content += f"""
            <p><strong>Autor:</strong> {form_data.get("author_name", "Não informado")}</p>
            <p><strong>Valor da Causa:</strong> R$ {form_data.get("valor_causa", "0,00")}</p>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ margin: 2.5cm 3cm; }}
                body {{ font-family: 'Times New Roman', serif; font-size: 12pt; 
                        line-height: 1.5; text-align: justify; }}
                h1 {{ font-size: 14pt; text-align: center; margin-top: 24pt; }}
                h2 {{ font-size: 12pt; margin-top: 18pt; }}
                p {{ text-indent: 2cm; margin-bottom: 12pt; }}
            </style>
        </head>
        <body>
            {template_content}
        </body>
        </html>
        """

        return PDFGenerationService.render_pdf_from_html(
            html_content, petition_type.name
        )


class SavedPetitionService:
    """Serviço para petições salvas"""

    @staticmethod
    def get_paginated(
        user_id: int,
        status_filter: str = "all",
        search: str = "",
    ) -> dict[str, Any]:
        """Obtém petições paginadas com estatísticas"""
        query = SavedPetitionRepository.get_by_user_filtered(
            user_id, status_filter, search
        )

        pagination = PaginationHelper(
            query=query,
            per_page=20,
            filters={"status": status_filter, "search": search},
        )

        stats = SavedPetitionRepository.get_stats(user_id)

        return {
            "petitions": pagination.items,
            "pagination": pagination,
            "stats": stats,
        }

    @staticmethod
    def get_with_access_check(
        petition_id: int, user_id: int
    ) -> tuple[SavedPetition | None, str | None]:
        """Obtém petição verificando acesso do usuário"""
        petition = SavedPetitionRepository.get_by_user_and_id(petition_id, user_id)

        if not petition:
            return None, "Petição não encontrada"

        return petition, None

    @staticmethod
    def get_for_edit(
        petition_id: int, user_id: int, petition_type_id: int
    ) -> SavedPetition | None:
        """Obtém petição para edição"""
        petition = SavedPetition.query.filter_by(
            id=petition_id,
            user_id=user_id,
            petition_type_id=petition_type_id,
        ).first()

        if petition and petition.status == "cancelled":
            return None

        return petition

    @staticmethod
    def save(
        user_id: int,
        data: dict[str, Any],
        petition_id: int | None = None,
        action: str | None = None,
    ) -> tuple[SavedPetition | None, str | None]:
        """Salva ou atualiza uma petição"""
        form_data = data.get("data", {})
        petition_type_id = data.get("petition_type_id")
        petition_model_id = data.get("petition_model_id")

        try:
            if petition_id:
                petition = SavedPetitionRepository.get_by_user_and_id(
                    petition_id, user_id
                )
                if not petition:
                    return None, "Petição não encontrada"
                if petition.status == "cancelled":
                    return None, "Petição cancelada não pode ser editada"
            else:
                petition = SavedPetition(
                    user_id=user_id,
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

            db.session.commit()

            # Gerar título automático
            if not petition.title:
                petition.title = SavedPetitionService._generate_title(
                    petition, form_data, petition_type_id, petition_model_id
                )
                db.session.commit()

            return petition, None

        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def _generate_title(
        petition: SavedPetition,
        form_data: dict,
        petition_type_id: int | None,
        petition_model_id: int | None,
    ) -> str:
        """Gera título automático para petição"""
        autor = form_data.get("autor_nome", "").strip()
        reu = form_data.get("reu_nome", "").strip()

        if petition_model_id:
            model = PetitionModelRepository.get_by_id(petition_model_id)
            base_name = model.name if model else "Modelo de Petição"
        elif petition_type_id:
            petition_type = db.session.get(PetitionType, petition_type_id)
            base_name = petition_type.name if petition_type else "Petição"
        else:
            base_name = "Petição"

        if autor and reu:
            return f"{base_name} - {autor} x {reu}"
        elif autor:
            return f"{base_name} - {autor}"
        else:
            return f"{base_name} - #{petition.id}"

    @staticmethod
    def cancel(petition_id: int, user_id: int) -> tuple[bool, str]:
        """Cancela uma petição"""
        petition, error = SavedPetitionService.get_with_access_check(
            petition_id, user_id
        )
        if error:
            return False, error

        if petition.status == "cancelled":
            return False, "Petição já está cancelada"

        SavedPetitionRepository.mark_cancelled(petition)
        return True, "Petição cancelada com sucesso!"

    @staticmethod
    def restore(petition_id: int, user_id: int) -> tuple[bool, str]:
        """Restaura uma petição cancelada"""
        petition, error = SavedPetitionService.get_with_access_check(
            petition_id, user_id
        )
        if error:
            return False, error

        if petition.status != "cancelled":
            return False, "Apenas petições canceladas podem ser restauradas"

        SavedPetitionRepository.restore(petition)
        return True, "Petição restaurada com sucesso!"

    @staticmethod
    def delete(petition_id: int, user_id: int) -> tuple[bool, str]:
        """Exclui uma petição permanentemente"""
        petition, error = SavedPetitionService.get_with_access_check(
            petition_id, user_id
        )
        if error:
            return False, error

        # Remover anexos físicos
        for attachment in petition.attachments:
            AttachmentService.delete_file(attachment.stored_filename)

        SavedPetitionRepository.delete(petition)
        return True, "Petição excluída permanentemente!"


class AttachmentService:
    """Serviço para anexos de petição"""

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Verifica se extensão é permitida"""
        return (
            "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    @staticmethod
    def get_upload_dir() -> str:
        """Obtém diretório de upload"""
        upload_dir = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "uploads"),
            "attachments",
        )
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir

    @staticmethod
    def delete_file(stored_filename: str) -> bool:
        """Exclui arquivo físico"""
        try:
            file_path = os.path.join(
                current_app.config.get("UPLOAD_FOLDER", "uploads"),
                "attachments",
                stored_filename,
            )
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def list_attachments(
        petition_id: int, user_id: int
    ) -> tuple[list | None, str | None]:
        """Lista anexos de uma petição"""
        petition = SavedPetitionRepository.get_by_user_and_id(petition_id, user_id)
        if not petition:
            return None, "Petição não encontrada"

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
                    "uploaded_at": att.uploaded_at.isoformat()
                    if att.uploaded_at
                    else None,
                }
            )

        return attachments, None

    @staticmethod
    def upload(
        petition_id: int,
        user_id: int,
        file: FileStorage,
        category: str = "prova",
        description: str = "",
    ) -> tuple[dict | None, str | None]:
        """Faz upload de um anexo"""
        petition = SavedPetitionRepository.get_by_user_and_id(petition_id, user_id)
        if not petition:
            return None, "Petição não encontrada"

        if petition.status == "cancelled":
            return None, "Não é possível anexar arquivos a petições canceladas"

        if not file or not file.filename:
            return None, "Nenhum arquivo enviado"

        if not AttachmentService.allowed_file(file.filename):
            return (
                None,
                f"Tipo de arquivo não permitido. Permitidos: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Verificar tamanho
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_ATTACHMENT_SIZE:
            max_mb = MAX_ATTACHMENT_SIZE // (1024 * 1024)
            return None, f"Arquivo muito grande. Máximo: {max_mb}MB por arquivo"

        # Verificar tamanho total
        current_total = PetitionAttachmentRepository.get_total_size(petition_id)
        if current_total + file_size > MAX_TOTAL_SIZE_PER_PETITION:
            remaining = (MAX_TOTAL_SIZE_PER_PETITION - current_total) // (1024 * 1024)
            return (
                None,
                f"Limite total de 50MB excedido. Espaço disponível: {remaining}MB",
            )

        # Gerar nome único
        original_filename = secure_filename(file.filename)
        ext = (
            original_filename.rsplit(".", 1)[1].lower()
            if "." in original_filename
            else ""
        )
        stored_filename = f"{uuid.uuid4().hex}.{ext}"

        # Salvar arquivo
        upload_dir = AttachmentService.get_upload_dir()
        file_path = os.path.join(upload_dir, stored_filename)
        file.save(file_path)

        # Criar registro
        attachment = PetitionAttachmentRepository.create(
            {
                "saved_petition_id": petition.id,
                "filename": original_filename,
                "stored_filename": stored_filename,
                "file_type": file.content_type,
                "file_size": file_size,
                "category": category,
                "description": description,
                "uploaded_by_id": user_id,
            }
        )

        return {
            "id": attachment.id,
            "filename": attachment.filename,
            "file_size_display": attachment.get_file_size_display(),
            "icon": attachment.get_icon(),
        }, None

    @staticmethod
    def delete(attachment_id: int, user_id: int) -> tuple[bool, str]:
        """Exclui um anexo"""
        attachment = PetitionAttachmentRepository.get_by_id(attachment_id)
        if not attachment:
            return False, "Anexo não encontrado"

        if attachment.saved_petition.user_id != user_id:
            return False, "Sem permissão"

        AttachmentService.delete_file(attachment.stored_filename)
        PetitionAttachmentRepository.delete(attachment)
        return True, "Anexo removido!"

    @staticmethod
    def get_file_path(
        attachment_id: int, user_id: int
    ) -> tuple[str | None, str | None, str | None]:
        """Obtém caminho do arquivo para download"""
        attachment = PetitionAttachmentRepository.get_by_id(attachment_id)
        if not attachment:
            return None, None, "Anexo não encontrado"

        if attachment.saved_petition.user_id != user_id:
            return None, None, "Sem permissão"

        file_path = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "uploads"),
            "attachments",
            attachment.stored_filename,
        )

        if not os.path.exists(file_path):
            return None, None, "Arquivo não encontrado"

        return file_path, attachment.filename, None


# Segunda SavedPetitionService removida - era duplicata da classe na linha 344
# Métodos get_user_petition_or_none, create_or_update, cancel, restore, delete_permanently
# já estão disponíveis na primeira SavedPetitionService como:
# - get_with_access_check, save, cancel, restore, delete
