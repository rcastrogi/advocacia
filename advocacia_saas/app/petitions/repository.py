"""
Petitions Repository - Camada de acesso a dados
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_

from app import db
from app.models import (
    PetitionAttachment,
    PetitionModel,
    PetitionSection,
    PetitionType,
    SavedPetition,
)


class PetitionTypeRepository:
    """Repositório para tipos de petição"""

    @staticmethod
    def get_by_id(type_id: int) -> PetitionType | None:
        """Obtém tipo de petição pelo ID"""
        return db.session.get(PetitionType, type_id)

    @staticmethod
    def get_by_slug(slug: str) -> PetitionType | None:
        """Obtém tipo de petição pelo slug"""
        return PetitionType.query.filter_by(slug=slug).first()

    @staticmethod
    def get_active() -> list[PetitionType]:
        """Obtém todos os tipos ativos"""
        return PetitionType.query.filter_by(is_active=True).all()


class PetitionModelRepository:
    """Repositório para modelos de petição"""

    @staticmethod
    def get_by_id(model_id: int) -> PetitionModel | None:
        """Obtém modelo pelo ID"""
        return db.session.get(PetitionModel, model_id)

    @staticmethod
    def get_by_slug(slug: str, active_only: bool = True) -> PetitionModel | None:
        """Obtém modelo pelo slug"""
        query = PetitionModel.query.filter_by(slug=slug)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.first()

    @staticmethod
    def get_active_for_type(petition_type_id: int) -> PetitionModel | None:
        """Obtém modelo ativo para um tipo de petição"""
        return PetitionModel.query.filter_by(
            petition_type_id=petition_type_id, is_active=True
        ).first()


class PetitionSectionRepository:
    """Repositório para seções de petição"""

    @staticmethod
    def get_by_id(section_id: int) -> PetitionSection | None:
        """Obtém seção pelo ID"""
        return db.session.get(PetitionSection, section_id)

    @staticmethod
    def get_active_by_id(section_id: int) -> PetitionSection | None:
        """Obtém seção ativa pelo ID"""
        section = db.session.get(PetitionSection, section_id)
        if section and section.is_active:
            return section
        return None


class SavedPetitionRepository:
    """Repositório para petições salvas"""

    @staticmethod
    def get_by_id(petition_id: int) -> SavedPetition | None:
        """Obtém petição pelo ID"""
        return db.session.get(SavedPetition, petition_id)

    @staticmethod
    def get_by_user_and_id(petition_id: int, user_id: int) -> SavedPetition | None:
        """Obtém petição pelo ID verificando o usuário"""
        return SavedPetition.query.filter_by(id=petition_id, user_id=user_id).first()

    @staticmethod
    def get_by_user_filtered(
        user_id: int,
        status: str | None = None,
        search: str | None = None,
    ):
        """Obtém query de petições filtradas por usuário"""
        query = SavedPetition.query.filter_by(user_id=user_id)

        if status and status != "all":
            query = query.filter_by(status=status)

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

        return query.order_by(SavedPetition.updated_at.desc())

    @staticmethod
    def get_stats(user_id: int) -> dict[str, int]:
        """Obtém estatísticas de petições do usuário"""
        return {
            "total": SavedPetition.query.filter_by(user_id=user_id).count(),
            "draft": SavedPetition.query.filter_by(
                user_id=user_id, status="draft"
            ).count(),
            "completed": SavedPetition.query.filter_by(
                user_id=user_id, status="completed"
            ).count(),
            "cancelled": SavedPetition.query.filter_by(
                user_id=user_id, status="cancelled"
            ).count(),
        }

    @staticmethod
    def create(data: dict[str, Any]) -> SavedPetition:
        """Cria uma nova petição salva"""
        petition = SavedPetition(**data)
        db.session.add(petition)
        db.session.commit()
        return petition

    @staticmethod
    def update(petition: SavedPetition, data: dict[str, Any]) -> SavedPetition:
        """Atualiza uma petição"""
        for key, value in data.items():
            if hasattr(petition, key):
                setattr(petition, key, value)
        db.session.commit()
        return petition

    @staticmethod
    def mark_completed(petition: SavedPetition) -> SavedPetition:
        """Marca petição como concluída"""
        petition.status = "completed"
        petition.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        return petition

    @staticmethod
    def mark_cancelled(petition: SavedPetition) -> SavedPetition:
        """Cancela uma petição"""
        petition.status = "cancelled"
        petition.cancelled_at = datetime.now(timezone.utc)
        db.session.commit()
        return petition

    @staticmethod
    def restore(petition: SavedPetition) -> SavedPetition:
        """Restaura uma petição cancelada"""
        petition.status = "draft"
        petition.cancelled_at = None
        db.session.commit()
        return petition

    @staticmethod
    def delete(petition: SavedPetition) -> None:
        """Exclui uma petição permanentemente"""
        db.session.delete(petition)
        db.session.commit()


class PetitionAttachmentRepository:
    """Repositório para anexos de petição"""

    @staticmethod
    def get_by_id(attachment_id: int) -> PetitionAttachment | None:
        """Obtém anexo pelo ID"""
        return db.session.get(PetitionAttachment, attachment_id)

    @staticmethod
    def get_by_petition(petition_id: int) -> list[PetitionAttachment]:
        """Obtém todos os anexos de uma petição"""
        return PetitionAttachment.query.filter_by(saved_petition_id=petition_id).all()

    @staticmethod
    def get_total_size(petition_id: int) -> int:
        """Obtém tamanho total de anexos de uma petição"""
        result = (
            db.session.query(db.func.sum(PetitionAttachment.file_size))
            .filter_by(saved_petition_id=petition_id)
            .scalar()
        )
        return result or 0

    @staticmethod
    def create(data: dict[str, Any]) -> PetitionAttachment:
        """Cria um novo anexo"""
        attachment = PetitionAttachment(**data)
        db.session.add(attachment)
        db.session.commit()
        return attachment

    @staticmethod
    def delete(attachment: PetitionAttachment) -> None:
        """Exclui um anexo"""
        db.session.delete(attachment)
        db.session.commit()
