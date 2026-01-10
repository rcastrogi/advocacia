"""
Decorators customizados para controle de acesso
"""

from functools import wraps

from flask import abort, flash, jsonify, redirect, request, url_for
from flask_login import current_user
from marshmallow import ValidationError


def lawyer_required(f):
    """
    Decorator que permite acesso apenas para advogados e master.
    Clientes são bloqueados.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # Bloquear clientes
        if current_user.user_type == "cliente":
            flash("Acesso negado. Esta área é exclusiva para advogados.", "danger")
            abort(403)

        # Permitir master e advogado
        return f(*args, **kwargs)

    return decorated_function


def master_required(f):
    """
    Decorator que permite acesso apenas para master.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        if current_user.user_type != "master":
            flash(
                "Acesso negado. Esta área é exclusiva para administradores.", "danger"
            )
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def validate_with_schema(schema_class, location="json"):
    """
    Decorator para validar dados de requisição com Marshmallow schema.

    Args:
        schema_class: Classe Marshmallow Schema
        location: 'json', 'form', ou 'args'

    Retorna erro 400 com mensagens de validação se falhar

    Uso:
        @app.route('/users', methods=['POST'])
        @validate_with_schema(UserSchema)
        def create_user():
            data = request.validated_data  # Dados validados
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import logging

            logger = logging.getLogger(__name__)

            schema = schema_class()

            # Validação só aplica em POST/PUT/PATCH
            if request.method not in ["POST", "PUT", "PATCH"]:
                logger.debug(
                    f"[validate_with_schema] Pulando validação para {request.method}"
                )
                return f(*args, **kwargs)

            logger.info(
                f"[validate_with_schema] {schema_class.__name__} - {request.method}"
            )
            logger.info(f"  Content-Type: {request.content_type}")

            try:
                # Obter dados da requisição
                if location == "json":
                    data = request.get_json(silent=True) or {}
                elif location == "form":
                    # Se form estiver vazio mas houver JSON, usar JSON
                    form_dict = request.form.to_dict()
                    json_data = request.get_json(silent=True)

                    if not form_dict and json_data:
                        logger.info(
                            f"  [INFO] Form vazio mas JSON presente. Usando JSON."
                        )
                        data = json_data
                    else:
                        data = form_dict

                    logger.info(
                        f"  Form data keys: {list(data.keys()) if data else 'vazio'}"
                    )
                elif location == "args":
                    data = request.args.to_dict()
                else:
                    data = request.get_json(silent=True) or {}

                if data is None:
                    data = {}

                # Validar com o schema
                validated_data = schema.load(data)
                logger.info(f"  [OK] Validacao passou")

                # Armazenar dados validados no request para acesso na função
                request.validated_data = validated_data

                return f(*args, **kwargs)

            except ValidationError as err:
                logger.error(f"  [ERRO] Validacao falhou")
                logger.error(f"  Erros: {err.messages}")

                # Retornar erros de validação como JSON
                if (
                    request.is_json
                    or request.accept_mimetypes.best == "application/json"
                ):
                    return jsonify(
                        {
                            "status": "error",
                            "message": "Erro de validação",
                            "errors": err.messages,
                        }
                    ), 400
                else:
                    # Para forms, redirecionar com mensagens de erro
                    for field, messages in err.messages.items():
                        if isinstance(messages, list):
                            for msg in messages:
                                flash(f"{field}: {msg}", "danger")
                        else:
                            flash(f"{field}: {messages}", "danger")
                    return redirect(request.referrer or url_for("admin.dashboard"))

        return decorated_function

    return decorator


def require_feature(feature_slug, redirect_to=None, message=None):
    """
    Decorator que verifica se o usuário tem acesso a uma feature específica.

    Usuários master sempre têm acesso.
    Outros usuários dependem do plano ativo ter a feature.

    Args:
        feature_slug: Slug da feature requerida (ex: 'ai_petitions', 'portal_cliente')
        redirect_to: Rota para redirecionar se não tiver acesso (default: billing.plans)
        message: Mensagem customizada para exibir

    Uso:
        @app.route('/ai/generate')
        @login_required
        @require_feature('ai_petitions')
        def generate_petition():
            ...

    Ou com parâmetros:
        @require_feature('portal_cliente', redirect_to='main.dashboard',
                         message='Atualize seu plano para acessar o Portal do Cliente')
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            # Verificar acesso à feature
            if not current_user.has_feature(feature_slug):
                # Mensagem padrão ou customizada
                default_message = f"Seu plano atual não inclui este recurso. Faça upgrade para acessar."
                flash_message = message or default_message
                flash(flash_message, "warning")

                # Para requisições AJAX/JSON
                if (
                    request.is_json
                    or request.accept_mimetypes.best == "application/json"
                ):
                    return jsonify(
                        {
                            "status": "error",
                            "error": "feature_not_available",
                            "message": flash_message,
                            "feature": feature_slug,
                            "upgrade_url": url_for("payments.plans", _external=True),
                        }
                    ), 403

                # Redirecionar para página de planos ou rota customizada
                target = redirect_to or "payments.plans"
                return redirect(url_for(target))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def check_feature_limit(feature_slug, current_count=None):
    """
    Decorator que verifica se o usuário atingiu o limite de uma feature.

    Útil para features com limite numérico (ex: máximo de processos, clientes).

    Args:
        feature_slug: Slug da feature com limite
        current_count: Função que retorna a contagem atual (ou None para calcular automaticamente)

    Uso:
        @app.route('/processes/new')
        @login_required
        @check_feature_limit('max_processes')
        def new_process():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))

            # Master não tem limites
            if current_user.is_master:
                return f(*args, **kwargs)

            # Obter limite da feature
            limit = current_user.get_feature_limit(feature_slug)

            # Se não tem limite (None ou -1), permitir
            if limit is None or limit == -1:
                return f(*args, **kwargs)

            # Calcular contagem atual se não fornecida
            if current_count is None:
                # Tentar calcular automaticamente baseado no feature_slug
                count = _get_automatic_count(feature_slug)
            else:
                count = current_count() if callable(current_count) else current_count

            # Verificar se atingiu limite
            if count >= limit:
                message = f"Você atingiu o limite de {limit} para este recurso. Faça upgrade para aumentar o limite."
                flash(message, "warning")

                if (
                    request.is_json
                    or request.accept_mimetypes.best == "application/json"
                ):
                    return jsonify(
                        {
                            "status": "error",
                            "error": "limit_reached",
                            "message": message,
                            "feature": feature_slug,
                            "limit": limit,
                            "current": count,
                            "upgrade_url": url_for("payments.plans", _external=True),
                        }
                    ), 403

                return redirect(url_for("payments.plans"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def _get_automatic_count(feature_slug):
    """
    Calcula automaticamente a contagem para features conhecidas.
    """
    from flask_login import current_user

    if feature_slug == "max_processes":
        from app.models import Process

        return Process.query.filter_by(lawyer_id=current_user.id).count()

    elif feature_slug == "max_clients":
        from app.models import Client

        return Client.query.filter_by(lawyer_id=current_user.id).count()

    elif feature_slug == "max_documents":
        from app.models import Document

        return Document.query.filter_by(user_id=current_user.id).count()

    # Se não souber calcular, retorna 0 (permite)
    return 0
