"""
Validadores customizados para formulários e dados
"""

import re
from typing import Tuple


def validate_strong_password(password: str) -> Tuple[bool, str]:
    """
    Valida se uma senha atende aos critérios de segurança.

    Critérios:
    - Mínimo 8 caracteres
    - Pelo menos uma letra maiúscula
    - Pelo menos uma letra minúscula
    - Pelo menos um número
    - Pelo menos um caractere especial

    Args:
        password: Senha a ser validada

    Returns:
        Tupla (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "A senha deve ter no mínimo 8 caracteres"

    if not re.search(r"[A-Z]", password):
        return False, "A senha deve conter pelo menos uma letra maiúscula"

    if not re.search(r"[a-z]", password):
        return False, "A senha deve conter pelo menos uma letra minúscula"

    if not re.search(r"\d", password):
        return False, "A senha deve conter pelo menos um número"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/]', password):
        return (
            False,
            "A senha deve conter pelo menos um caractere especial (!@#$%^&*...)",
        )

    # Verificar sequências comuns
    common_sequences = ["123456", "abcdef", "qwerty", "password", "senha"]
    password_lower = password.lower()
    for seq in common_sequences:
        if seq in password_lower:
            return False, f"A senha não pode conter sequências comuns como '{seq}'"

    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Valida formato de email.

    Args:
        email: Email a ser validado

    Returns:
        Tupla (is_valid, error_message)
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return False, "Formato de email inválido"

    if len(email) > 120:
        return False, "Email muito longo (máximo 120 caracteres)"

    return True, ""


def validate_oab_number(oab: str) -> Tuple[bool, str]:
    """
    Valida número de OAB (formato: UF + números).

    Args:
        oab: Número da OAB

    Returns:
        Tupla (is_valid, error_message)
    """
    if not oab:
        return True, ""  # OAB é opcional

    # Formato esperado: SP123456 ou SP 123456
    pattern = r"^[A-Z]{2}\s?\d{4,6}$"

    if not re.match(pattern, oab.upper()):
        return False, "Formato de OAB inválido (ex: SP123456)"

    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    Valida número de telefone brasileiro.

    Args:
        phone: Telefone a ser validado

    Returns:
        Tupla (is_valid, error_message)
    """
    if not phone:
        return True, ""  # Telefone é opcional

    # Remove caracteres não numéricos
    digits_only = re.sub(r"\D", "", phone)

    # Deve ter 10 ou 11 dígitos (com ou sem DDD)
    if len(digits_only) not in [10, 11]:
        return False, "Telefone deve ter 10 ou 11 dígitos (ex: 11987654321)"

    return True, ""


def validate_cpf(cpf: str) -> Tuple[bool, str]:
    """
    Valida CPF brasileiro.

    Args:
        cpf: CPF a ser validado (com ou sem formatação)

    Returns:
        Tupla (is_valid, error_message)
    """
    if not cpf:
        return True, ""  # CPF é opcional

    # Remove caracteres não numéricos
    cpf = re.sub(r"\D", "", cpf)

    # Deve ter 11 dígitos
    if len(cpf) != 11:
        return False, "CPF deve ter 11 dígitos"

    # Verifica se todos os dígitos são iguais (ex: 111.111.111-11)
    if len(set(cpf)) == 1:
        return False, "CPF inválido"

    # Calcula o primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[9]):
        return False, "CPF inválido"

    # Calcula o segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    if resto == 10 or resto == 11:
        resto = 0
    if resto != int(cpf[10]):
        return False, "CPF inválido"

    return True, ""


def validate_cnpj(cnpj: str) -> Tuple[bool, str]:
    """
    Valida CNPJ brasileiro.

    Args:
        cnpj: CNPJ a ser validado (com ou sem formatação)

    Returns:
        Tupla (is_valid, error_message)
    """
    if not cnpj:
        return True, ""  # CNPJ é opcional

    # Remove caracteres não numéricos
    cnpj = re.sub(r"\D", "", cnpj)

    # Deve ter 14 dígitos
    if len(cnpj) != 14:
        return False, "CNPJ deve ter 14 dígitos"

    # Verifica se todos os dígitos são iguais
    if len(set(cnpj)) == 1:
        return False, "CNPJ inválido"

    # Calcula o primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if digito1 != int(cnpj[12]):
        return False, "CNPJ inválido"

    # Calcula o segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    if digito2 != int(cnpj[13]):
        return False, "CNPJ inválido"

    return True, ""


def validate_cpf_cnpj(value: str) -> Tuple[bool, str]:
    """
    Valida CPF ou CNPJ brasileiro.
    Detecta automaticamente se é CPF (11 dígitos) ou CNPJ (14 dígitos).

    Args:
        value: CPF ou CNPJ a ser validado (com ou sem formatação)

    Returns:
        Tupla (is_valid, error_message)
    """
    if not value:
        return True, ""  # Valor é opcional

    # Remove caracteres não numéricos
    digits = re.sub(r"\D", "", value)

    # Determina se é CPF ou CNPJ pelo tamanho
    if len(digits) == 11:
        return validate_cpf(digits)
    elif len(digits) == 14:
        return validate_cnpj(digits)
    else:
        return False, "Informe um CPF (11 dígitos) ou CNPJ (14 dígitos) válido"


def sanitize_filename(filename: str) -> str:
    """
    Remove caracteres perigosos de nomes de arquivo.

    Args:
        filename: Nome do arquivo

    Returns:
        Nome sanitizado
    """
    # Remove caracteres perigosos
    filename = re.sub(r"[^\w\s\-\.]", "", filename)
    # Remove múltiplos espaços
    filename = re.sub(r"\s+", "_", filename)
    # Limita tamanho
    if len(filename) > 100:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:95] + ("." + ext if ext else "")

    return filename
