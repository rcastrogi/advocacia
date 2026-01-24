"""
Procuracao Repository - Camada de acesso a dados
"""

from app.models import Client


class ClientForProcuracaoRepository:
    """Repositório para buscar clientes para procurações"""

    @staticmethod
    def get_by_id(client_id: int) -> Client | None:
        return Client.query.get(client_id)

    @staticmethod
    def get_by_lawyer_ordered(lawyer_id: int) -> list[Client]:
        return (
            Client.query.filter_by(lawyer_id=lawyer_id).order_by(Client.full_name).all()
        )
