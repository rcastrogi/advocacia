"""
Office Repository - Camada de acesso a dados para escritório
"""

from datetime import datetime, timezone
from typing import Any

from app import db
from app.models import Office, OfficeInvite, User


class OfficeRepository:
    """Repositório para escritórios"""

    @staticmethod
    def get_by_id(office_id: int) -> Office | None:
        return db.session.get(Office, office_id)

    @staticmethod
    def get_by_slug(slug: str) -> Office | None:
        return Office.query.filter_by(slug=slug).first()

    @staticmethod
    def create(data: dict[str, Any], owner: User) -> Office:
        office = Office(
            name=data["name"],
            slug=Office.generate_slug(data["name"]),
            owner_id=owner.id,
            cnpj=data.get("cnpj") or None,
            oab_number=data.get("oab_number") or None,
            phone=data.get("phone") or None,
            email=data.get("email") or None,
            website=data.get("website") or None,
        )
        db.session.add(office)
        db.session.flush()  # Obter o ID

        # Vincular o owner ao escritório
        owner.office_id = office.id
        owner.office_role = "owner"

        db.session.commit()
        return office

    @staticmethod
    def update(office: Office, data: dict[str, Any]) -> Office:
        for key, value in data.items():
            if hasattr(office, key):
                setattr(office, key, value)
        office.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return office

    @staticmethod
    def delete(office: Office, owner: User) -> None:
        # Desvincular o owner
        owner.office_id = None
        owner.office_role = None

        # Excluir o escritório (cascata vai excluir convites)
        db.session.delete(office)
        db.session.commit()

    @staticmethod
    def get_members(office: Office) -> list[User]:
        return office.members.order_by(User.full_name).all()

    @staticmethod
    def get_active_members(office: Office) -> list[User]:
        return office.members.filter_by(is_active=True).all()

    @staticmethod
    def get_member_count(office: Office) -> int:
        return office.get_member_count()

    @staticmethod
    def can_add_member(office: Office) -> bool:
        return office.can_add_member()

    @staticmethod
    def get_max_members(office: Office) -> int:
        return office.get_max_members()


class OfficeMemberRepository:
    """Repositório para membros do escritório"""

    @staticmethod
    def get_by_id(member_id: int, office_id: int) -> User | None:
        return User.query.filter_by(id=member_id, office_id=office_id).first()

    @staticmethod
    def get_by_email(email: str, office_id: int) -> User | None:
        return User.query.filter_by(email=email, office_id=office_id).first()

    @staticmethod
    def change_role(member: User, new_role: str) -> None:
        member.office_role = new_role
        db.session.commit()

    @staticmethod
    def remove_member(office: Office, member: User) -> None:
        office.remove_member(member)
        db.session.commit()

    @staticmethod
    def get_eligible_for_ownership(office: Office, current_owner_id: int) -> list[User]:
        """Obtém membros elegíveis para receber a propriedade"""
        return office.members.filter(
            User.id != current_owner_id,
            User.is_active.is_(True),
        ).all()

    @staticmethod
    def transfer_ownership(office: Office, new_owner: User) -> None:
        office.transfer_ownership(new_owner)
        db.session.commit()


class OfficeInviteRepository:
    """Repositório para convites de escritório"""

    @staticmethod
    def get_by_id(invite_id: int, office_id: int) -> OfficeInvite | None:
        return OfficeInvite.query.filter_by(id=invite_id, office_id=office_id).first()

    @staticmethod
    def get_by_token(token: str) -> OfficeInvite | None:
        return OfficeInvite.query.filter_by(token=token).first()

    @staticmethod
    def get_pending_by_email(email: str, office_id: int) -> OfficeInvite | None:
        return OfficeInvite.query.filter_by(
            office_id=office_id, email=email, status="pending"
        ).first()

    @staticmethod
    def get_pending_count(office_id: int) -> int:
        return OfficeInvite.query.filter_by(office_id=office_id, status="pending").count()

    @staticmethod
    def get_pending_by_office(office: Office) -> list[OfficeInvite]:
        return (
            office.invites.filter_by(status="pending")
            .order_by(OfficeInvite.created_at.desc())
            .all()
        )

    @staticmethod
    def create(
        office_id: int, email: str, role: str, invited_by_id: int
    ) -> OfficeInvite | None:
        invite = OfficeInvite.create_invite(
            office_id=office_id,
            email=email,
            role=role,
            invited_by_id=invited_by_id,
        )
        if invite:
            db.session.commit()
        return invite

    @staticmethod
    def cancel(invite: OfficeInvite) -> None:
        invite.cancel()
        db.session.commit()

    @staticmethod
    def resend(invite: OfficeInvite) -> None:
        invite.resend()
        db.session.commit()

    @staticmethod
    def accept(invite: OfficeInvite, user: User) -> bool:
        result = invite.accept(user)
        if result:
            db.session.commit()
        return result

    @staticmethod
    def decline(invite: OfficeInvite) -> None:
        invite.status = "declined"
        db.session.commit()

    @staticmethod
    def get_inviters(invites: list[OfficeInvite]) -> dict[int, User]:
        """Obtém os usuários que enviaram os convites"""
        inviter_ids = set(invite.invited_by_id for invite in invites)
        if not inviter_ids:
            return {}
        users = User.query.filter(User.id.in_(inviter_ids)).all()
        return {u.id: u for u in users}
