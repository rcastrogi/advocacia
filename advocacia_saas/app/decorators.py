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
            logger.info(f"🔵 validate_with_schema: {schema_class.__name__}")
            logger.info(f"   Method: {request.method}")
            logger.info(f"   URL: {request.url}")
            logger.info(f"   Content-Type: {request.content_type}")
            logger.info(f"   Request Headers: {dict(request.headers)}")

            try:
                # Obter dados da requisição
                if location == "json":
                    data = request.get_json()
                elif location == "form":
                    # DEBUG: Ver exatamente o que vem no request
                    logger.info(f"   📝 request.form: {dict(request.form)}")
                    logger.info(f"   📝 request.json: {request.get_json()}")
                    logger.info(f"   📝 request.data (raw): {request.data}")
                    
                    # Se form estiver vazio mas houver JSON, usar JSON
                    form_dict = request.form.to_dict()
                    if not form_dict and request.is_json:
                        logger.warning(f"   ⚠️  Form vazio mas JSON presente. Usando JSON ao invés de form.")
                        data = request.get_json() or {}
                    else:
                        data = form_dict
                        
                    logger.info(f"   📝 Final data: {data}")
                elif location == "args":
                    data = request.args.to_dict()
                else:
                    data = request.get_json()

                if data is None:
                    data = {}

                # Validar com o schema
                validated_data = schema.load(data)
                logger.info(f"✅ Validação passou: {schema_class.__name__}")

                # Armazenar dados validados no request para acesso na função
                request.validated_data = validated_data

                return f(*args, **kwargs)

            except ValidationError as err:
                logger.error(f"❌ Validação falhou: {schema_class.__name__}")
                logger.error(f"   Erros: {err.messages}")
                
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
