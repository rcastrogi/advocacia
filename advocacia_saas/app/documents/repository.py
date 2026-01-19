"""
Documents Repository - Camada de Acesso a Dados.

Operações de banco de dados para documentos.
"""

from typing import Dict, List, Optional

from sqlalchemy import func

from app import db
from app.models import Client, Document


class DocumentRepository:
    """Repositório para operações com documentos."""

    @staticmethod
    def find_by_id(doc_id: int) -> Optional[Document]:
        """Busca documento pelo ID."""
        return Document.query.get(doc_id)

    @staticmethod
    def find_by_id_and_user(doc_id: int, user_id: int) -> Optional[Document]:
        """Busca documento pelo ID e usuário."""
        return Document.query.filter_by(id=doc_id, user_id=user_id).first()

    @staticmethod
    def search(
        user_id: int,
        client_id: Optional[int] = None,
        doc_type: Optional[str] = None,
        search_term: Optional[str] = None,
        status: str = "active",
    ):
        """Busca documentos com filtros."""
        query = Document.query.filter_by(user_id=user_id, status=status)

        if client_id:
            query = query.filter_by(client_id=client_id)

        if doc_type:
            query = query.filter_by(document_type=doc_type)

        if search_term:
            query = query.filter(
                db.or_(
                    Document.title.ilike(f"%{search_term}%"),
                    Document.description.ilike(f"%{search_term}%"),
                    Document.tags.ilike(f"%{search_term}%"),
                )
            )

        return query.order_by(Document.created_at.desc())

    @staticmethod
    def get_by_client(
        user_id: int, client_id: int, status: str = "active"
    ) -> List[Document]:
        """Lista documentos de um cliente."""
        return (
            Document.query.filter_by(
                user_id=user_id, client_id=client_id, status=status
            )
            .order_by(Document.created_at.desc())
            .all()
        )

    @staticmethod
    def search_for_api(user_id: int, query: str, limit: int = 10) -> List[Document]:
        """Busca documentos para API."""
        return (
            Document.query.filter(
                Document.user_id == user_id,
                Document.status == "active",
                db.or_(
                    Document.title.ilike(f"%{query}%"),
                    Document.description.ilike(f"%{query}%"),
                    Document.tags.ilike(f"%{query}%"),
                ),
            )
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_stats(user_id: int) -> Dict:
        """Obtém estatísticas de documentos."""
        total = Document.query.filter_by(user_id=user_id, status="active").count()

        by_type = (
            db.session.query(Document.document_type, func.count(Document.id))
            .filter_by(user_id=user_id, status="active")
            .group_by(Document.document_type)
            .all()
        )

        total_size = (
            db.session.query(func.sum(Document.file_size))
            .filter_by(user_id=user_id, status="active")
            .scalar()
            or 0
        )

        return {
            "total_documents": total,
            "by_type": dict(by_type),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    @staticmethod
    def create(user_id: int, **kwargs) -> Document:
        """Cria novo documento."""
        document = Document(user_id=user_id, **kwargs)
        db.session.add(document)
        db.session.commit()
        return document

    @staticmethod
    def save(document: Document):
        """Salva alterações no documento."""
        db.session.commit()

    @staticmethod
    def get_versions(document: Document) -> List[Document]:
        """Obtém versões de um documento."""
        if document.parent_document_id:
            parent = db.session.get(Document, document.parent_document_id)
            if parent:
                versions = (
                    Document.query.filter_by(parent_document_id=parent.id)
                    .order_by(Document.version.desc())
                    .all()
                )
                return [parent] + versions
        else:
            return document.versions.order_by(Document.version.desc()).all()
        return []


class ClientRepository:
    """Repositório para clientes no contexto de documentos."""

    @staticmethod
    def get_by_user(user_id: int) -> List[Client]:
        """Lista clientes do usuário."""
        return Client.query.filter_by(user_id=user_id).order_by(Client.name).all()

    @staticmethod
    def find_by_id_and_user(client_id: int, user_id: int) -> Optional[Client]:
        """Busca cliente pelo ID e usuário."""
        return Client.query.filter_by(id=client_id, user_id=user_id).first()
