"""
Office Services - Camada de lógica de negócios para escritório
"""

from typing import Any

from flask import url_for

# db removed - using repositories
from app.models import OFFICE_ROLES, User
from app.office.repository import (
    OfficeInviteRepository,
    OfficeMemberRepository,
    OfficeRepository,
)
from app.utils.email import send_office_invite_email


class OfficeService:
    """Serviço principal para gerenciamento de escritório"""

    @staticmethod
    def create_office(user: User, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Cria um novo escritório"""
        if user.office_id:
            return False, "Você já pertence a um escritório."

        office = OfficeRepository.create(form_data, user)
        return True, f"Escritório '{office.name}' criado com sucesso!"

    @staticmethod
    def update_settings(user: User, form_data: dict[str, Any]) -> tuple[bool, str]:
        """Atualiza configurações do escritório"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        OfficeRepository.update(office, form_data)
        return True, "Configurações salvas com sucesso!"

    @staticmethod
    def get_dashboard_data(user: User) -> dict[str, Any] | None:
        """Obtém dados para o dashboard do escritório"""
        office = user.get_office()
        if not office:
            return None

        members = OfficeRepository.get_active_members(office)
        pending_invites = OfficeInviteRepository.get_pending_count(office.id)
        max_members = OfficeRepository.get_max_members(office)

        return {
            "office": office,
            "members": members,
            "pending_invites": pending_invites,
            "max_members": max_members,
            "roles_info": OFFICE_ROLES,
            "can_manage": user.can_manage_office(),
            "is_owner": user.is_office_owner(),
        }

    @staticmethod
    def delete_office(user: User) -> tuple[bool, str]:
        """Exclui o escritório"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        member_count = OfficeRepository.get_member_count(office)
        if member_count > 1:
            return False, "Remova todos os membros antes de excluir o escritório."

        office_name = office.name
        OfficeRepository.delete(office, user)
        return True, f"Escritório '{office_name}' excluído com sucesso."


class OfficeMemberService:
    """Serviço para gerenciamento de membros do escritório"""

    @staticmethod
    def get_members_page_data(user: User) -> dict[str, Any] | None:
        """Obtém dados para a página de membros"""
        office = user.get_office()
        if not office:
            return None

        members = OfficeRepository.get_members(office)
        pending_invites = OfficeInviteRepository.get_pending_by_office(office)
        inviter_users = OfficeInviteRepository.get_inviters(pending_invites)

        return {
            "office": office,
            "members": members,
            "pending_invites": pending_invites,
            "inviter_users": inviter_users,
            "roles_info": OFFICE_ROLES,
            "can_manage": user.can_manage_office(),
            "is_owner": user.is_office_owner(),
            "can_add_member": OfficeRepository.can_add_member(office),
            "max_members": OfficeRepository.get_max_members(office),
        }

    @staticmethod
    def change_member_role(
        user: User, member_id: int, new_role: str
    ) -> tuple[bool, str]:
        """Altera a função de um membro"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        member = OfficeMemberRepository.get_by_id(member_id, office.id)
        if not member:
            return False, "Membro não encontrado."

        if member.office_role == "owner":
            return False, "Não é possível alterar a função do proprietário."

        if new_role == "admin" and not user.is_office_owner():
            return False, "Apenas o proprietário pode promover membros a administrador."

        if new_role not in OFFICE_ROLES:
            return False, "Função inválida."

        OfficeMemberRepository.change_role(member, new_role)
        role_name = OFFICE_ROLES[new_role]["name"]
        member_name = member.full_name or member.username
        return True, f"Função de {member_name} alterada para {role_name}."

    @staticmethod
    def remove_member(user: User, member_id: int) -> tuple[bool, str]:
        """Remove um membro do escritório"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        member = OfficeMemberRepository.get_by_id(member_id, office.id)
        if not member:
            return False, "Membro não encontrado."

        if member.office_role == "owner":
            return False, "Não é possível remover o proprietário do escritório."

        if member.office_role == "admin" and not user.is_office_owner():
            return False, "Apenas o proprietário pode remover administradores."

        if member.id == user.id:
            return False, "Você não pode se remover do escritório. Use 'Sair do Escritório' ao invés."

        member_name = member.full_name or member.username
        OfficeMemberRepository.remove_member(office, member)
        return True, f"{member_name} foi removido do escritório."

    @staticmethod
    def leave_office(user: User) -> tuple[bool, str]:
        """Sai do escritório"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        if user.is_office_owner():
            return False, "Você é o proprietário. Transfira a propriedade antes de sair ou exclua o escritório."

        office_name = office.name
        OfficeMemberRepository.remove_member(office, user)
        return True, f"Você saiu do escritório {office_name}."

    @staticmethod
    def get_transfer_candidates(user: User) -> list[tuple[int, str]]:
        """Obtém candidatos para transferência de propriedade"""
        office = user.get_office()
        if not office:
            return []

        eligible = OfficeMemberRepository.get_eligible_for_ownership(office, user.id)
        return [(m.id, f"{m.full_name or m.username} ({m.email})") for m in eligible]

    @staticmethod
    def transfer_ownership(user: User, new_owner_id: int) -> tuple[bool, str]:
        """Transfere a propriedade do escritório"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        new_owner = OfficeMemberRepository.get_by_id(new_owner_id, office.id)
        if not new_owner:
            return False, "Usuário inválido para transferência."

        OfficeMemberRepository.transfer_ownership(office, new_owner)
        new_owner_name = new_owner.full_name or new_owner.username
        return True, f"Propriedade transferida para {new_owner_name}."


class OfficeInviteService:
    """Serviço para gerenciamento de convites"""

    @staticmethod
    def send_invite(
        user: User, email: str, role: str
    ) -> tuple[bool, str, str | None]:
        """Envia um convite para novo membro"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado.", None

        if not OfficeRepository.can_add_member(office):
            max_members = OfficeRepository.get_max_members(office)
            return False, f"Limite de {max_members} membros atingido. Faça upgrade do plano para adicionar mais.", None

        email = email.lower()

        existing_invite = OfficeInviteRepository.get_pending_by_email(email, office.id)
        if existing_invite:
            return False, "Já existe um convite pendente para este e-mail.", None

        existing_member = OfficeMemberRepository.get_by_email(email, office.id)
        if existing_member:
            return False, "Este usuário já é membro do escritório.", None

        invite = OfficeInviteRepository.create(
            office_id=office.id,
            email=email,
            role=role,
            invited_by_id=user.id,
        )

        if not invite:
            return False, "Erro ao criar convite.", None

        email_sent = send_office_invite_email(invite)
        invite_url = url_for("office.accept_invite_page", token=invite.token, _external=True)

        if email_sent:
            return True, f"Convite enviado para {email}!", None
        else:
            return True, "Convite criado, mas não foi possível enviar o email.", invite_url

    @staticmethod
    def cancel_invite(user: User, invite_id: int) -> tuple[bool, str]:
        """Cancela um convite pendente"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado."

        invite = OfficeInviteRepository.get_by_id(invite_id, office.id)
        if not invite or invite.status != "pending":
            return False, "Convite não encontrado."

        OfficeInviteRepository.cancel(invite)
        return True, "Convite cancelado."

    @staticmethod
    def resend_invite(user: User, invite_id: int) -> tuple[bool, str, str | None]:
        """Reenvia um convite"""
        office = user.get_office()
        if not office:
            return False, "Escritório não encontrado.", None

        invite = OfficeInviteRepository.get_by_id(invite_id, office.id)
        if not invite or invite.status != "pending":
            return False, "Convite não encontrado.", None

        OfficeInviteRepository.resend(invite)
        email_sent = send_office_invite_email(invite)
        invite_url = url_for("office.accept_invite_page", token=invite.token, _external=True)

        if email_sent:
            return True, f"Convite reenviado para {invite.email}.", None
        else:
            return True, "Convite renovado, mas não foi possível enviar o email.", invite_url

    @staticmethod
    def validate_invite(token: str, user: User) -> tuple[bool, str, dict | None]:
        """Valida um convite para exibição"""
        invite = OfficeInviteRepository.get_by_token(token)

        if not invite:
            return False, "Convite não encontrado ou inválido.", None

        if not invite.is_valid():
            return False, "Este convite expirou ou já foi utilizado.", None

        if user.email.lower() != invite.email.lower():
            return False, "Este convite foi enviado para outro e-mail.", None

        if user.office_id:
            return False, "Você já pertence a um escritório. Saia primeiro para aceitar este convite.", None

        inviter = User.query.get(invite.invited_by_id)
        role_info = OFFICE_ROLES.get(invite.role, {})

        return True, "", {
            "invite": invite,
            "office": invite.office,
            "inviter": inviter,
            "role_info": role_info,
        }

    @staticmethod
    def accept_invite(token: str, user: User) -> tuple[bool, str]:
        """Aceita um convite"""
        invite = OfficeInviteRepository.get_by_token(token)

        if not invite or not invite.is_valid():
            return False, "Convite inválido ou expirado."

        if user.email.lower() != invite.email.lower():
            return False, "Este convite foi enviado para outro e-mail."

        if user.office_id:
            return False, "Você já pertence a um escritório."

        office = invite.office
        if not OfficeRepository.can_add_member(office):
            return False, "O escritório atingiu o limite de membros."

        if OfficeInviteRepository.accept(invite, user):
            return True, f"Bem-vindo ao escritório {office.name}!"
        else:
            return False, "Erro ao aceitar convite."

    @staticmethod
    def decline_invite(token: str, user: User) -> tuple[bool, str]:
        """Recusa um convite"""
        invite = OfficeInviteRepository.get_by_token(token)

        if not invite:
            return False, "Convite não encontrado."

        if user.email.lower() != invite.email.lower():
            return False, "Este convite foi enviado para outro e-mail."

        OfficeInviteRepository.decline(invite)
        return True, "Convite recusado."
