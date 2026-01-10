"""
Utilitários para filtragem de dados por escritório.

Este módulo fornece funções helper para ajustar as queries de modo que
membros de um escritório vejam apenas os dados compartilhados do escritório.
"""

from flask_login import current_user

from app import db


def get_office_user_ids():
    """
    Retorna uma lista de IDs de usuários que fazem parte do mesmo escritório
    do usuário atual.

    Se o usuário não pertence a um escritório, retorna apenas o ID dele.
    """
    if not current_user.is_authenticated:
        return []

    if current_user.office_id:
        # Buscar todos os membros do escritório
        from app.models import User

        members = User.query.filter_by(
            office_id=current_user.office_id, is_active=True
        ).all()
        return [m.id for m in members]
    else:
        # Usuário individual
        return [current_user.id]


def get_office_filter():
    """
    Retorna um filtro SQLAlchemy para usar em queries.

    Usage:
        from app.office.utils import get_office_filter

        # Em vez de:
        clients = Client.query.filter_by(lawyer_id=current_user.id).all()

        # Use:
        clients = Client.query.filter(Client.lawyer_id.in_(get_office_user_ids())).all()
        # ou
        clients = Client.query.filter(get_office_filter(Client.lawyer_id)).all()
    """
    user_ids = get_office_user_ids()
    return user_ids


def filter_by_office_member(model_class, field_name="lawyer_id"):
    """
    Retorna uma query base filtrada por escritório ou usuário.

    Args:
        model_class: Classe do modelo SQLAlchemy (Client, Process, etc)
        field_name: Nome do campo que representa o dono/responsável

    Returns:
        SQLAlchemy query filtrada

    Usage:
        from app.office.utils import filter_by_office_member

        # Em vez de:
        clients = Client.query.filter_by(lawyer_id=current_user.id)

        # Use:
        clients = filter_by_office_member(Client)
    """
    user_ids = get_office_user_ids()
    field = getattr(model_class, field_name)
    return model_class.query.filter(field.in_(user_ids))


def can_access_record(record, owner_field="lawyer_id"):
    """
    Verifica se o usuário atual pode acessar um registro específico.

    Args:
        record: O registro do banco de dados
        owner_field: Nome do campo que identifica o dono

    Returns:
        Boolean indicando se o usuário pode acessar
    """
    if not current_user.is_authenticated:
        return False

    record_owner_id = getattr(record, owner_field, None)
    if record_owner_id is None:
        return False

    # Se é o dono direto
    if record_owner_id == current_user.id:
        return True

    # Se são do mesmo escritório
    if current_user.office_id:
        from app.models import User

        owner = User.query.get(record_owner_id)
        if owner and owner.office_id == current_user.office_id:
            return True

    return False


def get_office_lawyers():
    """
    Retorna lista de advogados do escritório atual (para dropdowns).

    Returns:
        Lista de tuplas (id, nome) para uso em SelectField
    """
    if not current_user.is_authenticated:
        return []

    if current_user.office_id:
        from app.models import OFFICE_ROLES, User

        # Apenas advogados e admins podem ser responsáveis
        lawyers = (
            User.query.filter(
                User.office_id == current_user.office_id,
                User.is_active == True,
                User.office_role.in_(["owner", "admin", "lawyer"]),
            )
            .order_by(User.full_name)
            .all()
        )
        return [(l.id, l.full_name or l.username) for l in lawyers]
    else:
        return [(current_user.id, current_user.full_name or current_user.username)]
