"""
Utilitários para tratamento de mensagens de erro com feature toggle
"""

from flask import current_app


def get_error_message(error, generic_message="Ocorreu um erro. Tente novamente."):
    """
    Retorna mensagem de erro genérica ou real baseado na configuração.

    Args:
        error: Exception object ou string com o erro
        generic_message: Mensagem genérica a usar se SHOW_DETAILED_ERRORS for False

    Returns:
        String com a mensagem de erro a exibir ao usuário
    """
    try:
        # Verificar se deve mostrar erros detalhados (via variável de ambiente)
        show_detailed = current_app.config.get("SHOW_DETAILED_ERRORS", False)

        if show_detailed:
            # Retornar erro real
            error_msg = str(error)
            # Truncar para evitar expor informações sensíveis muito longas
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            return error_msg
        else:
            # Retornar mensagem genérica
            return generic_message
    except Exception:
        # Se algo der errado, sempre retornar mensagem genérica
        return generic_message


def format_error_for_user(error, error_type="general"):
    """
    Formata um erro de forma amigável ao usuário.

    Args:
        error: Exception object ou string
        error_type: Tipo de erro ('database', 'permission', 'validation', 'general')

    Returns:
        String formatada para exibir ao usuário
    """
    show_detailed = current_app.config.get("SHOW_DETAILED_ERRORS", False)

    if show_detailed:
        error_msg = str(error)
        return f"Erro ({error_type}): {error_msg[:150]}"

    # Mensagens genéricas por tipo
    messages = {
        "database": "Erro ao conectar ao banco de dados. Tente novamente em alguns instantes.",
        "permission": "Erro de permissão. Entre em contato com o administrador.",
        "validation": "Dados inválidos. Verifique os campos e tente novamente.",
        "network": "Erro de conexão. Tente novamente em alguns instantes.",
        "general": "Ocorreu um erro. Tente novamente.",
    }

    return messages.get(error_type, messages["general"])
