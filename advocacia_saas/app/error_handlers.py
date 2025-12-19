"""
Error handlers personalizados para o Petitio.
Transforma erros técnicos em mensagens amigáveis.
"""

import logging

from flask import flash, jsonify, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Registra handlers de erro customizados"""

    @app.errorhandler(400)
    def bad_request(error):
        """Erro 400 - Requisição inválida"""
        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Requisição inválida. Verifique os dados enviados.",
                    "code": 400,
                }
            ), 400

        flash(
            "Requisição inválida. Por favor, verifique os dados e tente novamente.",
            "danger",
        )
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(403)
    def forbidden(error):
        """Erro 403 - Acesso negado"""
        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Você não tem permissão para acessar este recurso.",
                    "code": 403,
                }
            ), 403

        flash("Você não tem permissão para acessar esta página.", "danger")
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        """Erro 404 - Página não encontrada"""
        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {"success": False, "error": "Recurso não encontrado.", "code": 404}
            ), 404

        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Erro 429 - Muitas requisições"""
        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Muitas tentativas. Por favor, aguarde alguns minutos e tente novamente.",
                    "code": 429,
                }
            ), 429

        flash(
            "Muitas tentativas em um curto período. Por favor, aguarde alguns minutos.",
            "warning",
        )
        return render_template("errors/429.html", error=error), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        """Erro 500 - Erro interno do servidor"""
        logger.error(f"Erro 500: {str(error)}", exc_info=True)

        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Ocorreu um erro interno. Nossa equipe foi notificada.",
                    "code": 500,
                }
            ), 500

        flash(
            "Ocorreu um erro inesperado. Nossa equipe foi notificada e está trabalhando para resolver.",
            "danger",
        )
        return render_template("errors/500.html", error=error), 500

    @app.errorhandler(503)
    def service_unavailable(error):
        """Erro 503 - Serviço indisponível"""
        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Serviço temporariamente indisponível. Tente novamente em instantes.",
                    "code": 503,
                }
            ), 503

        flash(
            "Serviço temporariamente indisponível. Por favor, tente novamente em alguns instantes.",
            "warning",
        )
        return render_template("errors/503.html", error=error), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Captura qualquer erro não tratado"""
        logger.error(f"Erro não tratado: {str(error)}", exc_info=True)

        # Se for um HTTPException, usar o código correto
        if isinstance(error, HTTPException):
            code = error.code
        else:
            code = 500

        if (
            request.is_json
            or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "Ocorreu um erro inesperado. Tente novamente ou entre em contato com o suporte.",
                    "code": code,
                }
            ), code

        flash("Ocorreu um erro inesperado. Por favor, tente novamente.", "danger")

        # Redirecionar para página anterior ou dashboard
        return redirect(request.referrer or url_for("main.index"))


def init_logging(app):
    """Configura sistema de logs"""
    if not app.debug:
        # Configurar handler de arquivo
        import os
        from logging.handlers import RotatingFileHandler

        if not os.path.exists("logs"):
            os.mkdir("logs")

        file_handler = RotatingFileHandler(
            "logs/petitio.log",
            maxBytes=10240000,  # 10MB
            backupCount=10,
        )

        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
            )
        )

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Petitio startup")
