"""
Serviços para APIs gerais
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from config import Config

from app.api.repository import CidadeRepository, ClientRepository, EstadoRepository

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Resposta padronizada de API."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int = 200


class EstadoService:
    """Serviço para Estados."""

    @staticmethod
    def listar_todos() -> List[Dict[str, Any]]:
        """Lista todos os estados."""
        estados = EstadoRepository.get_all()
        return [estado.to_dict() for estado in estados]


class CidadeService:
    """Serviço para Cidades."""

    @staticmethod
    def listar_por_estado(sigla: str) -> APIResponse:
        """Lista cidades de um estado pela sigla."""
        estado = EstadoRepository.get_by_sigla(sigla)

        if not estado:
            return APIResponse(
                success=False, error="Estado não encontrado", status_code=404
            )

        cidades = CidadeRepository.get_by_estado(estado.id)
        return APIResponse(
            success=True, data=[cidade.to_dict() for cidade in cidades]
        )


class CEPService:
    """Serviço para consulta de CEP via ViaCEP."""

    @staticmethod
    def consultar(cep: str) -> APIResponse:
        """Consulta CEP na API ViaCEP."""
        # Remove caracteres não numéricos
        clean_cep = "".join(filter(str.isdigit, cep))

        if len(clean_cep) != 8:
            return APIResponse(
                success=False, error="CEP deve conter 8 dígitos", status_code=400
            )

        formatted_cep = f"{clean_cep[:5]}-{clean_cep[5:]}"

        try:
            url = Config.CEP_API_URL.format(clean_cep)
            logger.info(f"Buscando CEP: {url}")

            response = requests.get(url, timeout=10, verify=True)
            logger.info(f"CEP response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if "erro" in data:
                    return APIResponse(
                        success=False, error="CEP não encontrado", status_code=404
                    )

                return APIResponse(
                    success=True,
                    data={
                        "cep": formatted_cep,
                        "street": data.get("logradouro", ""),
                        "neighborhood": data.get("bairro", ""),
                        "city": data.get("localidade", ""),
                        "uf": data.get("uf", ""),
                        "complement": data.get("complemento", ""),
                    },
                )
            else:
                logger.error(
                    f"CEP API retornou status {response.status_code}: {response.text[:200]}"
                )
                return APIResponse(
                    success=False, error="Erro ao consultar CEP", status_code=500
                )

        except requests.exceptions.Timeout:
            logger.error("Timeout na consulta do CEP")
            return APIResponse(
                success=False, error="Timeout na consulta do CEP", status_code=500
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão ao consultar CEP: {str(e)}")
            return APIResponse(
                success=False, error="Erro de conexão ao consultar CEP", status_code=500
            )
        except Exception as e:
            logger.error(f"Erro interno ao consultar CEP: {str(e)}")
            return APIResponse(
                success=False, error="Erro interno do servidor", status_code=500
            )


class ClientAPIService:
    """Serviço para operações de Cliente via API."""

    UPDATABLE_FIELDS = [
        "full_name",
        "email",
        "cpf_cnpj",
        "mobile_phone",
        "landline_phone",
        "rg",
        "civil_status",
        "birth_date",
        "profession",
        "nationality",
        "birth_place",
        "mother_name",
        "father_name",
        "address_type",
        "cep",
        "street",
        "number",
        "uf",
        "city",
        "neighborhood",
        "complement",
    ]

    @staticmethod
    def listar(lawyer_id: int) -> List[Dict[str, Any]]:
        """Lista clientes do advogado."""
        clients = ClientRepository.get_by_lawyer(lawyer_id)
        return [client.to_dict() for client in clients]

    @staticmethod
    def obter(client_id: int, lawyer_id: int) -> APIResponse:
        """Obtém um cliente específico."""
        client = ClientRepository.get_by_id_and_lawyer(client_id, lawyer_id)

        if not client:
            return APIResponse(
                success=False, error="Cliente não encontrado", status_code=404
            )

        return APIResponse(success=True, data=client.to_dict())

    @staticmethod
    def criar(lawyer_id: int, data: Dict[str, Any]) -> APIResponse:
        """Cria um novo cliente."""
        # Validar campos obrigatórios
        required_fields = ["full_name", "email", "cpf_cnpj", "mobile_phone"]
        for field in required_fields:
            if field not in data:
                return APIResponse(
                    success=False,
                    error=f"Campo {field} é obrigatório",
                    status_code=400,
                )

        # Verificar duplicidade de email
        if ClientRepository.get_by_email_and_lawyer(data["email"], lawyer_id):
            return APIResponse(
                success=False,
                error="Cliente com este email já existe",
                status_code=400,
            )

        # Verificar duplicidade de CPF/CNPJ
        if ClientRepository.get_by_cpf_and_lawyer(data["cpf_cnpj"], lawyer_id):
            return APIResponse(
                success=False,
                error="Cliente com este CPF/CNPJ já existe",
                status_code=400,
            )

        try:
            client = ClientRepository.create(lawyer_id=lawyer_id, **data)
            return APIResponse(success=True, data=client.to_dict(), status_code=201)
        except Exception as e:
            return APIResponse(
                success=False, error=f"Erro ao criar cliente: {str(e)}", status_code=500
            )

    @staticmethod
    def atualizar(client_id: int, lawyer_id: int, data: Dict[str, Any]) -> APIResponse:
        """Atualiza um cliente."""
        client = ClientRepository.get_by_id_and_lawyer(client_id, lawyer_id)

        if not client:
            return APIResponse(
                success=False, error="Cliente não encontrado", status_code=404
            )

        # Filtrar apenas campos permitidos
        update_data = {
            k: v for k, v in data.items() if k in ClientAPIService.UPDATABLE_FIELDS
        }

        try:
            updated_client = ClientRepository.update(client, **update_data)
            return APIResponse(success=True, data=updated_client.to_dict())
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Erro ao atualizar cliente: {str(e)}",
                status_code=500,
            )

    @staticmethod
    def deletar(client_id: int, lawyer_id: int) -> APIResponse:
        """Remove um cliente."""
        client = ClientRepository.get_by_id_and_lawyer(client_id, lawyer_id)

        if not client:
            return APIResponse(
                success=False, error="Cliente não encontrado", status_code=404
            )

        try:
            ClientRepository.delete(client)
            return APIResponse(success=True, data={"message": "Cliente excluído"})
        except Exception as e:
            return APIResponse(
                success=False,
                error=f"Erro ao excluir cliente: {str(e)}",
                status_code=500,
            )
