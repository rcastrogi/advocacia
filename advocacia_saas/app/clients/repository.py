"""
Repository para acesso a dados de Clientes.

Este módulo encapsula todas as operações de banco de dados relacionadas a clientes,
seguindo o padrão Repository para separar a lógica de acesso a dados da lógica de negócio.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_

from app import db
from app.models import Client, Dependent, User
from app.office.utils import filter_by_office_member, get_office_user_ids


class ClientRepository:
    """Repository para operações de banco de dados de Client."""

    @staticmethod
    def sanitize_cpf_cnpj(value: str) -> str:
        """Remove caracteres não numéricos do CPF/CNPJ para comparação."""
        if not value:
            return ""
        return re.sub(r"[^0-9]", "", value)

    @staticmethod
    def get_by_id(client_id: int) -> Optional[Client]:
        """Busca cliente por ID."""
        return Client.query.get(client_id)

    @staticmethod
    def get_by_id_or_404(client_id: int) -> Client:
        """Busca cliente por ID ou retorna 404."""
        return Client.query.get_or_404(client_id)

    @staticmethod
    def get_by_cpf_cnpj(
        cpf_cnpj: str,
        user: User,
        exclude_client_id: Optional[int] = None,
    ) -> Optional[Client]:
        """
        Busca cliente por CPF/CNPJ no escopo do usuário (escritório ou individual).

        Args:
            cpf_cnpj: CPF ou CNPJ a buscar
            user: Usuário atual para determinar escopo
            exclude_client_id: ID do cliente a excluir (para edição)

        Returns:
            Client se encontrado, None caso contrário
        """
        if not cpf_cnpj:
            return None

        sanitized = ClientRepository.sanitize_cpf_cnpj(cpf_cnpj)
        if len(sanitized) < 11:  # CPF mínimo tem 11 dígitos
            return None

        # Determinar escopo: escritório ou advogado individual
        if user.office_id:
            office_user_ids = get_office_user_ids()
            query = Client.query.filter(
                or_(
                    Client.office_id == user.office_id,
                    Client.lawyer_id.in_(office_user_ids),
                )
            )
        else:
            query = Client.query.filter(Client.lawyer_id == user.id)

        if exclude_client_id:
            query = query.filter(Client.id != exclude_client_id)

        # Comparar CPF/CNPJ normalizado
        for client in query.all():
            if ClientRepository.sanitize_cpf_cnpj(client.cpf_cnpj) == sanitized:
                return client

        return None

    @staticmethod
    def list_for_user(user: User):
        """
        Retorna query de clientes visíveis para o usuário.

        Args:
            user: Usuário atual

        Returns:
            SQLAlchemy query ordenada por data de criação
        """
        return filter_by_office_member(Client, "lawyer_id").order_by(
            Client.created_at.desc()
        )

    @staticmethod
    def create(data: dict, user: User) -> Client:
        """
        Cria um novo cliente.

        Args:
            data: Dados do cliente (do formulário)
            user: Usuário que está criando

        Returns:
            Cliente criado
        """
        client = Client(
            office_id=user.office_id,
            lawyer_id=user.id,
            full_name=data.get("full_name"),
            rg=data.get("rg"),
            cpf_cnpj=data.get("cpf_cnpj"),
            civil_status=data.get("civil_status"),
            birth_date=data.get("birth_date"),
            profession=data.get("profession"),
            nationality=data.get("nationality"),
            birth_place=data.get("birth_place"),
            mother_name=data.get("mother_name"),
            father_name=data.get("father_name"),
            address_type=data.get("address_type"),
            cep=data.get("cep"),
            street=data.get("street"),
            number=data.get("number"),
            complement=data.get("complement"),
            neighborhood=data.get("neighborhood"),
            city=data.get("city"),
            uf=data.get("uf"),
            landline_phone=data.get("landline_phone"),
            email=data.get("email"),
            mobile_phone=data.get("mobile_phone"),
            lgbt_declared=data.get("lgbt_declared", False),
            has_disability=data.get("has_disability", False),
            disability_types=data.get("disability_types"),
            is_pregnant_postpartum=data.get("is_pregnant_postpartum", False),
            delivery_date=data.get("delivery_date"),
        )

        db.session.add(client)
        db.session.flush()  # Obter ID antes do commit

        # Adicionar advogado como principal
        client.add_lawyer(user, is_primary=True)

        return client

    @staticmethod
    def update(client: Client, data: dict) -> Client:
        """
        Atualiza um cliente existente.

        Args:
            client: Cliente a atualizar
            data: Novos dados

        Returns:
            Cliente atualizado
        """
        for field in [
            "full_name", "rg", "cpf_cnpj", "civil_status", "birth_date",
            "profession", "nationality", "birth_place", "mother_name",
            "father_name", "address_type", "cep", "street", "number",
            "complement", "neighborhood", "city", "uf", "landline_phone",
            "email", "mobile_phone", "lgbt_declared", "has_disability",
            "disability_types", "is_pregnant_postpartum", "delivery_date",
        ]:
            if field in data:
                setattr(client, field, data[field])

        client.updated_at = datetime.now(timezone.utc)
        return client

    @staticmethod
    def delete(client: Client) -> None:
        """Remove um cliente."""
        db.session.delete(client)

    @staticmethod
    def add_dependents(client: Client, dependents_data: list) -> None:
        """
        Adiciona dependentes a um cliente.

        Args:
            client: Cliente
            dependents_data: Lista de dicionários com dados dos dependentes
        """
        for dep_data in dependents_data:
            if dep_data.get("full_name"):
                dependent = Dependent(
                    client_id=client.id,
                    full_name=dep_data.get("full_name"),
                    relationship=dep_data.get("relationship"),
                    birth_date=dep_data.get("birth_date"),
                    cpf=dep_data.get("cpf"),
                )
                db.session.add(dependent)

    @staticmethod
    def clear_dependents(client: Client) -> None:
        """Remove todos os dependentes de um cliente."""
        for dependent in client.dependents:
            db.session.delete(dependent)

    @staticmethod
    def commit() -> None:
        """Persiste as alterações no banco."""
        db.session.commit()

    @staticmethod
    def rollback() -> None:
        """Desfaz alterações pendentes."""
        db.session.rollback()
