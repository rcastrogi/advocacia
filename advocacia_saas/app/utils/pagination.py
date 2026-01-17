"""
Sistema Universal de Paginação para o Petitio

Oferece um helper para padronizar paginação em todas as listagens.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from flask import request, url_for


class PaginationHelper:
    """
    Helper universal para gerenciar paginação de forma consistente.

    Uso:
        pagination = PaginationHelper(
            query=User.query,
            per_page=20,
            url_func=lambda page: url_for('admin.users_list', page=page, search=search),
            filters={'search': search, 'status': status}
        )

        users = pagination.items
        template_context = pagination.to_dict()  # para templates
    """

    DEFAULT_PER_PAGE = 20
    MAX_PER_PAGE = 100

    def __init__(
        self,
        query,
        per_page: Optional[int] = None,
        url_func: Optional[Callable] = None,
        filters: Optional[Dict[str, Any]] = None,
        error_out: bool = False,
    ):
        """
        Inicializar paginação.

        Args:
            query: SQLAlchemy Query object
            per_page: Itens por página (default 20, max 100)
            url_func: Função para gerar URLs (não obrigatória)
            filters: Dicionário com filtros ativos (para templates)
            error_out: Se True, retorna erro em página inválida
        """
        self.page = max(1, request.args.get("page", 1, type=int))
        self.per_page = per_page or self.DEFAULT_PER_PAGE

        # Limitar per_page para evitar abuso
        self.per_page = min(self.per_page, self.MAX_PER_PAGE)

        self.url_func = url_func
        self.filters = filters or {}
        self.error_out = error_out

        # Executar paginação
        self.paginated = query.paginate(
            page=self.page, per_page=self.per_page, error_out=error_out
        )

    @property
    def items(self) -> List[Any]:
        """Retorna itens da página atual."""
        return self.paginated.items

    @property
    def total(self) -> int:
        """Total de itens."""
        return self.paginated.total

    @property
    def pages(self) -> int:
        """Total de páginas."""
        return self.paginated.pages

    @property
    def has_prev(self) -> bool:
        """Se tem página anterior."""
        return self.paginated.has_prev

    @property
    def has_next(self) -> bool:
        """Se tem próxima página."""
        return self.paginated.has_next

    @property
    def prev_num(self) -> Optional[int]:
        """Número da página anterior."""
        return self.paginated.prev_num

    @property
    def next_num(self) -> Optional[int]:
        """Número da próxima página."""
        return self.paginated.next_num

    def iter_pages(
        self,
        left_edge: int = 2,
        left_current: int = 2,
        right_current: int = 2,
        right_edge: int = 2,
    ):
        """
        Iterar sobre números de página a exibir.

        Args:
            left_edge: Páginas a mostrar no início
            left_current: Páginas a mostrar à esquerda da atual
            right_current: Páginas a mostrar à direita da atual
            right_edge: Páginas a mostrar no fim

        Yields:
            Número da página ou None (para "...")
        """
        return self.paginated.iter_pages(
            left_edge=left_edge,
            left_current=left_current,
            right_current=right_current,
            right_edge=right_edge,
        )

    def get_url(self, page: int) -> str:
        """
        Gerar URL para uma página específica.

        Args:
            page: Número da página

        Returns:
            URL completa (se url_func fornecida)
        """
        if not self.url_func:
            return f"?page={page}"
        return self.url_func(page)

    def to_dict(self) -> Dict[str, Any]:
        """
        Retornar dicionário para usar em templates.

        Returns:
            Dicionário com todas as propriedades de paginação
        """
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": self.total,
            "pages": self.pages,
            "has_prev": self.has_prev,
            "has_next": self.has_next,
            "prev_num": self.prev_num,
            "next_num": self.next_num,
            "items": self.items,
            "filters": self.filters,
            "iter_pages": lambda **kwargs: self.iter_pages(**kwargs),
            "get_url": self.get_url,
            # Para compatibilidade com Flask-SQLAlchemy.Pagination
            "paginated": self.paginated,
        }

    def __iter__(self):
        """Permitir iteração direta sobre items."""
        return iter(self.items)

    def __len__(self):
        """Retornar tamanho da página atual."""
        return len(self.items)

    def __repr__(self):
        return (
            f"<PaginationHelper page={self.page} "
            f"per_page={self.per_page} total={self.total} pages={self.pages}>"
        )


def get_pagination_params() -> Tuple[int, int]:
    """
    Extrair e validar parâmetros de paginação da query string.

    Returns:
        Tupla (page, per_page)
        - page: Número da página (min 1)
        - per_page: Itens por página (min 10, max 100)
    """
    page = max(1, request.args.get("page", 1, type=int))
    per_page = request.args.get("per_page", PaginationHelper.DEFAULT_PER_PAGE, type=int)

    # Validar per_page
    if per_page < 10:
        per_page = 10
    elif per_page > PaginationHelper.MAX_PER_PAGE:
        per_page = PaginationHelper.MAX_PER_PAGE

    return page, per_page


def build_pagination_context(
    pagination, extra_filters: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Construir contexto de paginação para templates.

    Compatível com tanto PaginationHelper quanto Flask-SQLAlchemy.Pagination.

    Args:
        pagination: Objeto de paginação
        extra_filters: Filtros adicionais para incluir no contexto

    Returns:
        Dicionário pronto para passar ao template
    """
    if isinstance(pagination, PaginationHelper):
        context = pagination.to_dict()
    else:
        # Flask-SQLAlchemy Pagination
        context = {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "prev_num": pagination.prev_num,
            "next_num": pagination.next_num,
            "items": pagination.items,
            "iter_pages": pagination.iter_pages,
        }

    if extra_filters:
        context["filters"] = extra_filters

    return context
