"""
Procuracao Repository - Camada de acesso a dados
"""

from sqlalchemy import or_

from app.models import Client, User


class ClientForProcuracaoRepository:
    """Repositório para buscar clientes para procurações"""

    @staticmethod
    def get_by_id(client_id: int) -> Client | None:
        return Client.query.get(client_id)

    @staticmethod
    def get_by_lawyer_ordered(lawyer_id: int) -> list[Client]:
        return (
            Client.query.outerjoin(User, Client.user_id == User.id)
            .filter(Client.lawyer_id == lawyer_id)
            .filter(or_(Client.user_id.is_(None), User.user_type != "master"))
            .order_by(Client.full_name)
            .all()
        )
