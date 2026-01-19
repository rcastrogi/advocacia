"""
Documents Services - Camada de Lógica de Negócio.

Serviços para gestão de documentos.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from werkzeug.utils import secure_filename

from app import db
from app.documents.repository import ClientRepository, DocumentRepository
from app.models import Client, Document
from app.utils.pagination import PaginationHelper

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif", "zip", "rar"
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@dataclass
class UploadResult:
    """Resultado de upload de documento."""

    success: bool
    document: Optional[Document] = None
    error_message: Optional[str] = None


class DocumentService:
    """Serviço principal de documentos."""

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Verifica se extensão é permitida."""
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
        )

    @classmethod
    def list_documents(
        cls,
        user_id: int,
        client_id: Optional[int] = None,
        doc_type: Optional[str] = None,
        search: Optional[str] = None,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        Lista documentos com filtros e paginação.

        Returns:
            Dicionário com documentos paginados e metadados.
        """
        query = DocumentRepository.search(
            user_id, client_id=client_id, doc_type=doc_type, search_term=search
        )

        pagination = PaginationHelper(
            query=query,
            per_page=per_page,
            filters={"client": client_id, "type": doc_type, "search": search},
        )

        clients = ClientRepository.get_by_user(user_id)

        return {
            "documents": pagination.items,
            "clients": clients,
            "selected_client": client_id,
            "doc_type": doc_type,
            "search": search,
            "pagination": pagination.to_dict(),
        }

    @classmethod
    def upload_document(
        cls,
        file,
        user_id: int,
        client_id: int,
        title: str,
        description: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        is_visible_to_client: bool = False,
        is_confidential: bool = False,
    ) -> UploadResult:
        """
        Faz upload de documento.

        Returns:
            UploadResult com sucesso ou erro.
        """
        # Validações
        if not file or file.filename == "":
            return UploadResult(success=False, error_message="Nenhum arquivo selecionado")

        if not cls.allowed_file(file.filename):
            return UploadResult(success=False, error_message="Tipo de arquivo não permitido")

        if not client_id or not title:
            return UploadResult(
                success=False, error_message="Cliente e título são obrigatórios"
            )

        # Salvar arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"

        upload_folder = os.path.join(
            current_app.root_path, "static", "uploads", "documents"
        )
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        file_size = os.path.getsize(filepath)
        file_extension = "." + filename.rsplit(".", 1)[1].lower()

        # Criar documento no banco
        document = DocumentRepository.create(
            user_id=user_id,
            client_id=client_id,
            title=title,
            description=description,
            document_type=document_type,
            category=category,
            filename=filename,
            file_path=f"uploads/documents/{unique_filename}",
            file_size=file_size,
            file_type=file.content_type,
            file_extension=file_extension,
            tags=tags,
            is_visible_to_client=is_visible_to_client,
            is_confidential=is_confidential,
        )

        return UploadResult(success=True, document=document)

    @classmethod
    def get_document(cls, doc_id: int, user_id: int) -> Optional[Document]:
        """Busca documento verificando permissão."""
        return DocumentRepository.find_by_id_and_user(doc_id, user_id)

    @classmethod
    def get_document_with_versions(
        cls, doc_id: int, user_id: int
    ) -> Tuple[Optional[Document], List[Document]]:
        """
        Busca documento com suas versões.

        Returns:
            Tupla (document, versions)
        """
        document = DocumentRepository.find_by_id_and_user(doc_id, user_id)
        if not document:
            return None, []

        document.mark_accessed()
        versions = DocumentRepository.get_versions(document)

        return document, versions

    @classmethod
    def update_document(
        cls,
        document: Document,
        title: str,
        description: Optional[str] = None,
        document_type: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        is_visible_to_client: bool = False,
        is_confidential: bool = False,
        notes: Optional[str] = None,
    ):
        """Atualiza metadados do documento."""
        document.title = title
        document.description = description
        document.document_type = document_type
        document.category = category
        document.tags = tags
        document.is_visible_to_client = is_visible_to_client
        document.is_confidential = is_confidential
        document.notes = notes

        DocumentRepository.save(document)

    @classmethod
    def create_new_version(
        cls, document: Document, file, user_id: int
    ) -> Tuple[Optional[Document], Optional[str]]:
        """
        Cria nova versão do documento.

        Returns:
            Tupla (new_document, error_message)
        """
        if not file or file.filename == "":
            return None, "Nenhum arquivo selecionado"

        if not cls.allowed_file(file.filename):
            return None, "Arquivo inválido"

        # Salvar arquivo
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{filename}"

        upload_folder = os.path.join(
            current_app.root_path, "static", "uploads", "documents"
        )
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)

        file_size = os.path.getsize(filepath)

        # Criar nova versão usando método do modelo
        new_doc = document.create_new_version(
            f"uploads/documents/{unique_filename}",
            filename,
            file_size,
            user_id,
        )

        return new_doc, None

    @classmethod
    def archive_document(cls, document: Document):
        """Arquiva documento."""
        document.archive()

    @classmethod
    def delete_document(cls, document: Document):
        """Deleta documento (soft delete)."""
        document.delete_document()

    @classmethod
    def get_download_info(
        cls, doc_id: int, user_id: int
    ) -> Tuple[Optional[Tuple[str, str, str]], Optional[str]]:
        """
        Obtém informações para download.

        Returns:
            Tupla ((directory, filename, download_name), error_message)
        """
        document = DocumentRepository.find_by_id_and_user(doc_id, user_id)
        if not document:
            return None, "Documento não encontrado"

        if not document.file_path:
            return None, "Arquivo não encontrado"

        document.mark_accessed()

        directory = os.path.dirname(
            os.path.join(current_app.root_path, "static", document.file_path)
        )
        filename = os.path.basename(document.file_path)

        return (directory, filename, document.filename), None

    @classmethod
    def get_documents_by_client(
        cls, client_id: int, user_id: int
    ) -> Tuple[Optional[Client], List[Document]]:
        """
        Lista documentos de um cliente.

        Returns:
            Tupla (client, documents)
        """
        client = ClientRepository.find_by_id_and_user(client_id, user_id)
        if not client:
            return None, []

        documents = DocumentRepository.get_by_client(user_id, client_id)
        return client, documents


class DocumentSearchService:
    """Serviço de busca de documentos."""

    @staticmethod
    def search(user_id: int, query: str) -> List[Dict]:
        """Busca documentos para API."""
        if len(query) < 2:
            return []

        documents = DocumentRepository.search_for_api(user_id, query)
        return [doc.to_dict() for doc in documents]

    @staticmethod
    def get_stats(user_id: int) -> Dict:
        """Obtém estatísticas de documentos."""
        return DocumentRepository.get_stats(user_id)
