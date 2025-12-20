"""
Validador de números OAB
Consulta o cadastro oficial da OAB para validar números e nomes
"""

import re
from typing import Dict, Optional

import requests

# Estados válidos da OAB
ESTADOS_OAB = [
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
]


def validar_formato_oab(numero_oab: str) -> bool:
    """
    Valida o formato do número OAB: UF + números

    Exemplos válidos:
    - SP123456
    - RJ98765
    - MG123456A

    Args:
        numero_oab: Número da OAB a validar

    Returns:
        True se o formato é válido, False caso contrário
    """
    if not numero_oab:
        return False

    # Remove espaços e converte para maiúscula
    numero_oab = numero_oab.strip().upper()

    # Padrão: UF + 4 a 6 dígitos + opcional letra
    pattern = r"^([A-Z]{2})(\d{4,6})([A-Z])?$"
    match = re.match(pattern, numero_oab)

    if not match:
        return False

    uf = match.group(1)
    return uf in ESTADOS_OAB


def extrair_uf_numero(numero_oab: str) -> Optional[Dict[str, str]]:
    """
    Extrai UF e número da OAB

    Args:
        numero_oab: Número da OAB

    Returns:
        Dicionário com 'uf', 'numero' e 'letra' ou None
    """
    if not numero_oab:
        return None

    numero_oab = numero_oab.strip().upper()
    pattern = r"^([A-Z]{2})(\d{4,6})([A-Z])?$"
    match = re.match(pattern, numero_oab)

    if not match:
        return None

    return {
        "uf": match.group(1),
        "numero": match.group(2),
        "letra": match.group(3) or "",
    }


def consultar_oab_online(numero_oab: str, timeout: int = 10) -> Dict[str, any]:
    """
    Consulta informações da OAB online

    ATENÇÃO: A OAB não possui API pública oficial. Esta função é um placeholder
    para quando uma API estiver disponível ou para integração com serviços pagos.

    Por enquanto, retorna apenas validação de formato.

    Args:
        numero_oab: Número da OAB a consultar
        timeout: Tempo limite da requisição

    Returns:
        Dicionário com informações:
        {
            'valido': bool,
            'formato_valido': bool,
            'numero': str,
            'uf': str,
            'nome': str (se disponível),
            'situacao': str (se disponível),
            'mensagem': str
        }
    """
    resultado = {
        "valido": False,
        "formato_valido": False,
        "numero": numero_oab,
        "uf": None,
        "nome": None,
        "situacao": None,
        "mensagem": "",
    }

    # Validar formato
    if not validar_formato_oab(numero_oab):
        resultado["mensagem"] = (
            "Formato de OAB inválido. Use o formato: UF + números (ex: SP123456)"
        )
        return resultado

    resultado["formato_valido"] = True
    dados = extrair_uf_numero(numero_oab)
    resultado["uf"] = dados["uf"]

    # TODO: Implementar consulta real quando API estiver disponível
    # Opções futuras:
    # 1. API oficial da OAB (se disponível)
    # 2. Serviço pago de consulta (ReceitaWS, etc)
    # 3. Web scraping do portal da OAB (não recomendado)

    # Por enquanto, aceita qualquer OAB com formato válido
    resultado["valido"] = True
    resultado["mensagem"] = "Formato válido. Consulta online não disponível no momento."

    return resultado


def validar_oab_com_nome(numero_oab: str, nome_advogado: str) -> Dict[str, any]:
    """
    Valida OAB e verifica correspondência com nome do advogado

    Args:
        numero_oab: Número da OAB
        nome_advogado: Nome do advogado a validar

    Returns:
        Dicionário com resultado da validação
    """
    resultado = consultar_oab_online(numero_oab)

    # Se não temos o nome do cadastro online, não podemos validar
    if resultado["valido"] and not resultado["nome"]:
        resultado["nome_valido"] = None
        resultado["mensagem"] += " Verificação de nome não disponível."
    elif resultado["nome"]:
        # Comparar nomes (simplificado)
        nome_cadastro = resultado["nome"].lower().strip()
        nome_informado = nome_advogado.lower().strip()
        resultado["nome_valido"] = (
            nome_cadastro in nome_informado or nome_informado in nome_cadastro
        )

        if not resultado["nome_valido"]:
            resultado["mensagem"] = (
                f"Nome não corresponde ao cadastro. Cadastrado: {resultado['nome']}"
            )

    return resultado


# Função auxiliar para uso em formulários
def validar_oab_field(numero_oab: str) -> tuple[bool, str]:
    """
    Validação simples para uso em forms do Flask

    Returns:
        (é_válido, mensagem_erro)
    """
    if not numero_oab:
        return False, "Número OAB é obrigatório"

    resultado = consultar_oab_online(numero_oab)

    if not resultado["formato_valido"]:
        return False, resultado["mensagem"]

    if not resultado["valido"]:
        return False, resultado["mensagem"]

    return True, ""
