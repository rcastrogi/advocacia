import os
import zoneinfo
from datetime import datetime, timezone

from config import Config
from flask import Flask
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
socketio = SocketIO()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
cache = Cache()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure timezone for Brazil (São Paulo)
    app.config["TIMEZONE"] = zoneinfo.ZoneInfo("America/Sao_Paulo")
    app.config["TIMEZONE_NAME"] = "America/Sao_Paulo"

    # Configure JSON and response encoding
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"

    # Initialize Sentry for error tracking
    if app.config.get("SENTRY_DSN"):
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=app.config["SENTRY_DSN"],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            environment=app.config.get("ENV", "production"),
        )

    # Initialize security headers (HTTPS, HSTS, CSP)
    if app.config.get("FORCE_HTTPS", False):
        Talisman(
            app,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy={
                "default-src": ["'self'"],
                "script-src": [
                    "'self'",
                    "'unsafe-inline'",  # Necessário para Alpine.js inline
                    "'unsafe-eval'",  # Necessário para Alpine.js expressions
                    "cdn.jsdelivr.net",
                    "unpkg.com",
                    "cdnjs.cloudflare.com",
                    "code.jquery.com",
                ],
                "style-src": [
                    "'self'",
                    "'unsafe-inline'",
                    "cdn.jsdelivr.net",
                    "cdnjs.cloudflare.com",
                    "fonts.googleapis.com",
                ],
                "font-src": ["'self'", "fonts.gstatic.com", "cdnjs.cloudflare.com"],
                "img-src": ["'self'", "data:", "https:"],
                "connect-src": ["'self'"],
            },
        )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Initialize email notifications system
    from app.processes.email_notifications import init_mail
    init_mail(app)

    # Initialize rate limiter only if enabled
    if app.config.get("RATELIMIT_ENABLED", True):
        # Use Redis for rate limiting if available, otherwise memory
        storage_uri = "memory://"
        if app.config.get("REDIS_URL"):
            # Usar DB específico para rate limiting
            redis_url = app.config.get("REDIS_URL")
            ratelimit_db = app.config.get("REDIS_RATELIMIT_DB", 1)
            storage_uri = f"{redis_url}/{ratelimit_db}"
        limiter.storage_uri = storage_uri
        limiter.init_app(app)

    # socketio.init_app(app, cors_allowed_origins="*")

    # Initialize cache
    if app.config.get("REDIS_URL"):
        cache.init_app(
            app,
            config={
                "CACHE_TYPE": "RedisCache",
                "CACHE_REDIS_URL": f"{app.config.get('REDIS_URL')}/{app.config.get('REDIS_CACHE_DB', 0)}",
                "CACHE_DEFAULT_TIMEOUT": app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
                "CACHE_KEY_PREFIX": app.config.get("CACHE_KEY_PREFIX", "petitio"),
                "CACHE_REDIS_DB": app.config.get("REDIS_CACHE_DB", 0),
            },
        )
    else:
        cache.init_app(
            app,
            config={
                "CACHE_TYPE": "SimpleCache",
                "CACHE_DEFAULT_TIMEOUT": app.config.get("CACHE_DEFAULT_TIMEOUT", 300),
            },
        )

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "info"

    # Create upload directory if it doesn't exist
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    # Register blueprints
    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.clients import bp as clients_bp

    app.register_blueprint(clients_bp, url_prefix="/clients")

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    from app.petitions import bp as petitions_bp

    app.register_blueprint(petitions_bp, url_prefix="/petitions")

    from app.billing import bp as billing_bp

    app.register_blueprint(billing_bp, url_prefix="/billing")

    # Removido: checkout blueprint (Stripe) - sistema usa apenas Mercado Pago

    from app.ai import ai_bp

    app.register_blueprint(ai_bp)

    from app.admin import bp as admin_bp

    app.register_blueprint(admin_bp)

    from app.payments import bp as payments_bp

    app.register_blueprint(payments_bp)

    from app.deadlines import bp as deadlines_bp

    app.register_blueprint(deadlines_bp)

    from app.chat import bp as chat_bp

    app.register_blueprint(chat_bp)

    from app.portal import bp as portal_bp

    app.register_blueprint(portal_bp)

    from app.documents import bp as documents_bp

    app.register_blueprint(documents_bp)

    from app.oab_validation import bp as oab_validation_bp

    app.register_blueprint(oab_validation_bp)

    from app.procuracao import bp as procuracao_bp

    app.register_blueprint(procuracao_bp, url_prefix="/procuracao")

    from app.lgpd import lgpd_bp

    app.register_blueprint(lgpd_bp)

    from app.processes import bp as processes_bp

    app.register_blueprint(processes_bp, url_prefix="/processes")

    from app.advanced import advanced_bp

    app.register_blueprint(advanced_bp)

    # Register error handlers
    from app.error_handlers import init_logging, register_error_handlers

    register_error_handlers(app)
    init_logging(app)

    # Register custom Jinja2 filters
    @app.template_filter("local_datetime")
    def local_datetime_filter(
        dt, format_string="%d/%m/%Y às %H:%M", user_timezone=None
    ):
        """Convert UTC datetime to local timezone (user's timezone or São Paulo by default)"""
        if dt is None:
            return "-"
        if dt.tzinfo is None:
            # Assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)

        # Use user timezone if provided, otherwise use app default
        if user_timezone:
            try:
                target_tz = zoneinfo.ZoneInfo(user_timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                target_tz = app.config["TIMEZONE"]
        else:
            target_tz = app.config["TIMEZONE"]

        local_dt = dt.astimezone(target_tz)
        return local_dt.strftime(format_string)

    @app.template_filter("local_date")
    def local_date_filter(dt, format_string="%d/%m/%Y", user_timezone=None):
        """Convert UTC date to local timezone (user's timezone or São Paulo by default)"""
        if dt is None:
            return "-"
        if hasattr(dt, "tzinfo") and dt.tzinfo is None:
            # Assume UTC if naive
            dt = dt.replace(tzinfo=timezone.utc)
        elif not hasattr(dt, "tzinfo"):
            # If it's a date object, convert to datetime first
            dt = datetime.combine(dt, datetime.min.time())
            dt = dt.replace(tzinfo=timezone.utc)

        # Use user timezone if provided, otherwise use app default
        if user_timezone:
            try:
                target_tz = zoneinfo.ZoneInfo(user_timezone)
            except zoneinfo.ZoneInfoNotFoundError:
                target_tz = app.config["TIMEZONE"]
        else:
            target_tz = app.config["TIMEZONE"]

        local_dt = dt.astimezone(target_tz)
        return local_dt.strftime(format_string)

    # Register markdown filter
    try:
        import markdown

        @app.template_filter("markdown")
        def markdown_filter(text):
            """Convert markdown text to HTML"""
            if not text:
                return ""
            return markdown.markdown(text, extensions=["extra", "codehilite"])
    except ImportError:

        @app.template_filter("markdown")
        def markdown_filter(text):
            """Fallback markdown filter if markdown library is not available"""
            if not text:
                return ""
            # Simple fallback - just return text with basic formatting
            return text.replace("\n", "<br>")

    return app
