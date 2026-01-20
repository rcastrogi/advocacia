"""
Repositórios para APIs gerais
"""

from typing import List, Optional

from app.models import Cidade, Client, Estado


class EstadoRepository:
    """Repositório para Estados."""

    @staticmethod
    def get_all() -> List[Estado]:
        """Lista todos os estados ordenados por nome."""
        return Estado.query.order_by(Estado.nome).all()

    @staticmethod
    def get_by_sigla(sigla: str) -> Optional[Estado]:
        """Busca estado pela sigla."""
        return Estado.query.filter_by(sigla=sigla.upper()).first()


class CidadeRepository:
    """Repositório para Cidades."""

    @staticmethod
    def get_by_estado(estado_id: int) -> List[Cidade]:
        """Lista cidades de um estado."""
        return Cidade.query.filter_by(estado_id=estado_id).order_by(Cidade.nome).all()


class ClientRepository:
    """Repositório para Clientes via API."""

    @staticmethod
    def get_by_lawyer(lawyer_id: int) -> List[Client]:
        """Lista clientes de um advogado."""
        return Client.query.filter_by(lawyer_id=lawyer_id).all()

    @staticmethod
    def get_by_id_and_lawyer(client_id: int, lawyer_id: int) -> Optional[Client]:
        """Busca cliente por ID e advogado."""
        return Client.query.filter_by(id=client_id, lawyer_id=lawyer_id).first()

    @staticmethod
    def get_by_email_and_lawyer(email: str, lawyer_id: int) -> Optional[Client]:
        """Busca cliente por email e advogado."""
        return Client.query.filter_by(email=email, lawyer_id=lawyer_id).first()

    @staticmethod
    def get_by_cpf_and_lawyer(cpf_cnpj: str, lawyer_id: int) -> Optional[Client]:
        """Busca cliente por CPF/CNPJ e advogado."""
        return Client.query.filter_by(cpf_cnpj=cpf_cnpj, lawyer_id=lawyer_id).first()

    @staticmethod
    def create(lawyer_id: int, **data) -> Client:
        """Cria um novo cliente."""
        from app import db

        client = Client(lawyer_id=lawyer_id, **data)
        db.session.add(client)
        db.session.commit()
        return client

    @staticmethod
    def update(client: Client, **data) -> Client:
        """Atualiza um cliente."""
        from app import db

        for key, value in data.items():
            if hasattr(client, key):
                setattr(client, key, value)
        db.session.commit()
        return client

    @staticmethod
    def delete(client: Client) -> None:
        """Remove um cliente."""
        from app import db

        db.session.delete(client)
        db.session.commit()
