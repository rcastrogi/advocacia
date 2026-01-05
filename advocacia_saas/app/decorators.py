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
                logger.debug(f"[validate_with_schema] Pulando validação para {request.method}")
                return f(*args, **kwargs)
            
            logger.info(f"[validate_with_schema] {schema_class.__name__} - {request.method}")
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
                        logger.info(f"  [INFO] Form vazio mas JSON presente. Usando JSON.")
                        data = json_data
                    else:
                        data = form_dict
                        
                    logger.info(f"  Form data keys: {list(data.keys()) if data else 'vazio'}")
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
