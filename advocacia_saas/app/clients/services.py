"""
Service para lógica de negócio de Clientes.

Este módulo contém toda a lógica de negócio relacionada a clientes,
incluindo validações, regras de negócio e orquestração de operações.
"""

from dataclasses import dataclass
from typing import Optional

from app.clients.repository import ClientRepository
from app.models import Client, User
from app.office.utils import can_access_record
from app.utils.audit import AuditManager


@dataclass
class ServiceResult:
    """Resultado padronizado de operações de serviço."""

    success: bool
    data: Optional[any] = None
    error: Optional[str] = None
    error_type: str = "warning"  # warning, danger, info


class ClientService:
    """Service para operações de negócio de Client."""

    def __init__(self, repository: ClientRepository = None):
        self.repository = repository or ClientRepository()

    def list_clients(self, user: User):
        """
        Lista clientes visíveis para o usuário.

        Args:
            user: Usuário atual

        Returns:
            Query de clientes
        """
        return self.repository.list_for_user(user)

    def get_client(self, client_id: int, user: User) -> ServiceResult:
        """
        Busca um cliente verificando permissão de acesso.

        Args:
            client_id: ID do cliente
            user: Usuário atual

        Returns:
            ServiceResult com cliente ou erro
        """
        client = self.repository.get_by_id(client_id)

        if not client:
            return ServiceResult(success=False, error="Cliente não encontrado", error_type="danger")

        if not can_access_record(client, "lawyer_id"):
            return ServiceResult(success=False, error="Sem permissão para acessar este cliente", error_type="danger")

        return ServiceResult(success=True, data=client)

    def check_duplicate(
        self,
        cpf_cnpj: str,
        user: User,
        exclude_client_id: Optional[int] = None,
    ) -> Optional[Client]:
        """
        Verifica se existe cliente com mesmo CPF/CNPJ no escopo.

        Args:
            cpf_cnpj: CPF ou CNPJ a verificar
            user: Usuário atual (para escopo)
            exclude_client_id: ID a excluir da busca (edição)

        Returns:
            Cliente duplicado se existir, None caso contrário
        """
        return self.repository.get_by_cpf_cnpj(cpf_cnpj, user, exclude_client_id)

    def create_client(self, form_data: dict, dependents_data: list, user: User) -> ServiceResult:
        """
        Cria um novo cliente com validações de negócio.

        Args:
            form_data: Dados do formulário
            dependents_data: Lista de dependentes
            user: Usuário que está criando

        Returns:
            ServiceResult com cliente criado ou erro
        """
        # Validar duplicidade de CPF/CNPJ
        existing = self.check_duplicate(form_data.get("cpf_cnpj"), user)
        if existing:
            return ServiceResult(
                success=False,
                error=f"Já existe um cliente cadastrado com este CPF/CNPJ: {existing.full_name}. "
                      "Verifique os dados ou acesse o cadastro existente.",
                error_type="warning",
            )

        try:
            # Criar cliente
            client = self.repository.create(form_data, user)

            # Adicionar dependentes
            if dependents_data:
                self.repository.add_dependents(client, dependents_data)

            self.repository.commit()

            # Registrar auditoria
            AuditManager.log_client_change(
                client,
                "create",
                new_values={
                    "full_name": client.full_name,
                    "email": client.email,
                    "cpf_cnpj": client.cpf_cnpj,
                    "mobile_phone": client.mobile_phone,
                    "profession": client.profession,
                    "city": client.city,
                    "uf": client.uf,
                },
            )

            return ServiceResult(success=True, data=client)

        except Exception as e:
            self.repository.rollback()
            return ServiceResult(success=False, error=f"Erro ao criar cliente: {str(e)}", error_type="danger")

    def update_client(
        self,
        client_id: int,
        form_data: dict,
        dependents_data: list,
        user: User,
    ) -> ServiceResult:
        """
        Atualiza um cliente existente.

        Args:
            client_id: ID do cliente
            form_data: Novos dados
            dependents_data: Lista de dependentes
            user: Usuário que está atualizando

        Returns:
            ServiceResult com cliente atualizado ou erro
        """
        # Buscar cliente com verificação de acesso
        result = self.get_client(client_id, user)
        if not result.success:
            return result

        client = result.data

        # Verificar duplicidade se CPF/CNPJ foi alterado
        new_cpf = form_data.get("cpf_cnpj")
        if new_cpf and new_cpf != client.cpf_cnpj:
            existing = self.check_duplicate(new_cpf, user, exclude_client_id=client_id)
            if existing:
                return ServiceResult(
                    success=False,
                    error=f"Já existe outro cliente cadastrado com este CPF/CNPJ: {existing.full_name}. "
                          "Verifique os dados.",
                    error_type="warning",
                )

        try:
            # Capturar valores antigos para auditoria
            old_values = self._get_audit_values(client)

            # Atualizar cliente
            self.repository.update(client, form_data)

            # Atualizar dependentes
            self.repository.clear_dependents(client)
            if dependents_data:
                self.repository.add_dependents(client, dependents_data)

            self.repository.commit()

            # Registrar auditoria
            new_values = self._get_audit_values(client)
            changed_fields = [k for k in old_values if old_values[k] != new_values[k]]

            if changed_fields:
                AuditManager.log_client_change(
                    client, "update", old_values, new_values, changed_fields
                )

            return ServiceResult(success=True, data=client)

        except Exception as e:
            self.repository.rollback()
            return ServiceResult(success=False, error=f"Erro ao atualizar cliente: {str(e)}", error_type="danger")

    def delete_client(self, client_id: int, user: User) -> ServiceResult:
        """
        Remove um cliente.

        Args:
            client_id: ID do cliente
            user: Usuário que está removendo

        Returns:
            ServiceResult indicando sucesso ou erro
        """
        # Apenas o dono pode deletar
        client = Client.query.filter_by(id=client_id, lawyer_id=user.id).first()

        if not client:
            return ServiceResult(success=False, error="Cliente não encontrado ou sem permissão", error_type="danger")

        try:
            self.repository.delete(client)
            self.repository.commit()
            return ServiceResult(success=True)

        except Exception as e:
            self.repository.rollback()
            return ServiceResult(success=False, error=f"Erro ao excluir cliente: {str(e)}", error_type="danger")

    def add_lawyer_to_client(
        self,
        client_id: int,
        lawyer_email: str,
        specialty: Optional[str],
        user: User,
    ) -> ServiceResult:
        """
        Adiciona um advogado a um cliente.

        Args:
            client_id: ID do cliente
            lawyer_email: Email do advogado a adicionar
            specialty: Especialidade (opcional)
            user: Usuário atual

        Returns:
            ServiceResult indicando sucesso ou erro
        """
        client = self.repository.get_by_id(client_id)

        if not client:
            return ServiceResult(success=False, error="Cliente não encontrado", error_type="danger")

        # Verificar acesso
        if not client.has_lawyer(user) and client.lawyer_id != user.id:
            return ServiceResult(success=False, error="Sem permissão", error_type="danger")

        if not lawyer_email:
            return ServiceResult(success=False, error="Email do advogado é obrigatório", error_type="danger")

        # Buscar advogado
        lawyer = User.query.filter_by(email=lawyer_email).first()

        if not lawyer:
            return ServiceResult(success=False, error="Advogado não encontrado com este email", error_type="danger")

        if lawyer.user_type not in ["advogado", "escritorio"]:
            return ServiceResult(success=False, error="Este usuário não é um advogado", error_type="danger")

        if client.has_lawyer(lawyer):
            return ServiceResult(success=False, error="Este advogado já está associado ao cliente", error_type="warning")

        try:
            client.add_lawyer(lawyer, specialty=specialty)
            self.repository.commit()
            return ServiceResult(
                success=True,
                data={"lawyer_name": lawyer.full_name or lawyer.username},
            )

        except Exception as e:
            self.repository.rollback()
            return ServiceResult(success=False, error=str(e), error_type="danger")

    def remove_lawyer_from_client(
        self,
        client_id: int,
        lawyer_id: int,
        user: User,
    ) -> ServiceResult:
        """
        Remove um advogado de um cliente.

        Args:
            client_id: ID do cliente
            lawyer_id: ID do advogado a remover
            user: Usuário atual

        Returns:
            ServiceResult indicando sucesso ou erro
        """
        client = self.repository.get_by_id(client_id)

        if not client:
            return ServiceResult(success=False, error="Cliente não encontrado", error_type="danger")

        # Verificar acesso
        if not client.has_lawyer(user) and client.lawyer_id != user.id:
            return ServiceResult(success=False, error="Sem permissão", error_type="danger")

        # Não permitir remover advogado principal
        if lawyer_id == client.lawyer_id:
            return ServiceResult(success=False, error="Não é possível remover o advogado principal", error_type="danger")

        lawyer = User.query.get(lawyer_id)

        if not lawyer:
            return ServiceResult(success=False, error="Advogado não encontrado", error_type="danger")

        if not client.has_lawyer(lawyer):
            return ServiceResult(success=False, error="Este advogado não está associado ao cliente", error_type="warning")

        try:
            client.remove_lawyer(lawyer)
            self.repository.commit()
            return ServiceResult(
                success=True,
                data={"lawyer_name": lawyer.full_name or lawyer.username},
            )

        except Exception as e:
            self.repository.rollback()
            return ServiceResult(success=False, error=str(e), error_type="danger")

    def _get_audit_values(self, client: Client) -> dict:
        """Extrai valores para auditoria."""
        return {
            "full_name": client.full_name,
            "email": client.email,
            "cpf_cnpj": client.cpf_cnpj,
            "mobile_phone": client.mobile_phone,
            "profession": client.profession,
            "civil_status": client.civil_status,
            "cep": client.cep,
            "street": client.street,
            "city": client.city,
            "uf": client.uf,
            "neighborhood": client.neighborhood,
        }


# Instância singleton para uso nas rotas
client_service = ClientService()
