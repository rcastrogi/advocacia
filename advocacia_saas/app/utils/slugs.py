"""
Funções utilitárias para geração de slugs
"""

import re
from typing import Type

from sqlalchemy.orm import Query

from app import db


def slugify(value: str, max_length: int = 100) -> str:
    """
    Converte uma string em um slug válido.

    Args:
        value: String a ser convertida
        max_length: Tamanho máximo do slug (default: 100)

    Returns:
        Slug válido (letras minúsculas, números e hífens)
    """
    if not value:
        return ""

    # Converter para minúsculas e remover espaços extras
    value = value.strip().lower()

    # Substituir caracteres especiais e espaços por hífens
    value = re.sub(r"[^a-z0-9]+", "-", value)

    # Remover hífens do início e fim
    slug = value.strip("-")

    # Truncar se necessário, garantindo que não corte no meio de uma palavra
    if len(slug) > max_length:
        slug = slug[:max_length]
        # Remover hífen no final se ficou truncado
        slug = slug.rstrip("-")

    return slug


def generate_unique_slug(
    base_name: str, model_class: Type, existing_slug: str = None
) -> str:
    """
    Gera um slug único baseado no nome fornecido.

    Se o slug já existir, adiciona um número sequencial até encontrar um disponível.

    Args:
        base_name: Nome base para gerar o slug
        model_class: Classe do modelo que contém o campo slug
        existing_slug: Slug atual (para casos de edição, onde o slug atual é permitido)

    Returns:
        Slug único
    """
    base_slug = slugify(base_name)

    if not base_slug:
        base_slug = "slug"

    # Se não há slug existente ou o slug gerado é diferente do existente, verificar unicidade
    if not existing_slug or base_slug != existing_slug:
        # Verificar se o slug base já existe
        query = db.session.query(model_class).filter(model_class.slug == base_slug)

        # Se estamos editando, excluir o registro atual da verificação
        if existing_slug:
            query = query.filter(model_class.slug != existing_slug)

        if not query.first():
            return base_slug

        # Se existe, adicionar números sequenciais
        counter = 1
        while True:
            candidate_slug = f"{base_slug}-{counter}"
            query = db.session.query(model_class).filter(
                model_class.slug == candidate_slug
            )

            if existing_slug:
                query = query.filter(model_class.slug != existing_slug)

            if not query.first():
                return candidate_slug

            counter += 1

    return base_slug
