import hashlib
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
from flask_wtf.csrf import CSRFProtect

# Inicializar logging ANTES de qualquer coisa
from logging_config import setup_production_logging

setup_production_logging()

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
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Desabilitar cache de arquivos estáticos em desenvolvimento
    if app.debug:
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    # Configure timezone for Brazil (São Paulo)
    app.config["TIMEZONE"] = zoneinfo.ZoneInfo("America/Sao_Paulo")
    app.config["TIMEZONE_NAME"] = "America/Sao_Paulo"

    # Configure JSON and response encoding
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"

    # ✅ Setup logging centralizado
    from app.logger_config import setup_logging

    setup_logging(app)

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
    
    # Initialize CSRF protection for all forms
    csrf.init_app(app)

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

    # Import all models to ensure they're registered with SQLAlchemy
    # This MUST be done before any db.create_all() calls
    from app.models import (  # noqa: F401, E402
        OFFICE_ROLES,
        AgendaBlock,
        AIGeneration,
        AuditLog,
        BillingPlan,
        Client,
        CreditPackage,
        Feature,
        Office,
        OfficeInvite,
        Payment,
        PetitionModel,
        PetitionModelSection,
        PetitionSection,
        PetitionType,
        PetitionUsage,
        Process,
        RoadmapCategory,
        RoadmapFeedback,
        RoadmapItem,
        SavedPetition,
        Testimonial,
        User,
        UserCredits,
        UserPlan,
    )

    # Import roadmap voting models
    from app.models_roadmap_votes import (  # noqa: F401, E402
        RoadmapVote,
        RoadmapVoteQuota,
    )

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

    from app.office import bp as office_bp

    app.register_blueprint(office_bp, url_prefix="/office")

    from app.processes import bp as processes_bp

    app.register_blueprint(processes_bp, url_prefix="/processes")

    from app.advanced import advanced_bp

    app.register_blueprint(advanced_bp)

    # Register roadmap voting API
    from app.api_roadmap_votes import roadmap_votes_bp

    app.register_blueprint(roadmap_votes_bp)

    # Register logs visualization routes
    from app.logs_routes import bp as logs_bp

    app.register_blueprint(logs_bp)

    # Register referral program routes
    from app.referral import bp as referral_bp

    app.register_blueprint(referral_bp)

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

    # Register audit helpers as template globals
    from app.utils.audit_helpers import (
        format_action_badge,
        format_entity_reference,
        format_entity_type_badge,
        get_action_badge_config,
        get_entity_badge_config,
    )

    app.jinja_env.filters["entity_badge"] = format_entity_type_badge
    app.jinja_env.filters["action_badge"] = format_action_badge
    app.jinja_env.filters["entity_reference"] = (
        lambda entity_type, entity_id: format_entity_reference(entity_type, entity_id)
    )

    app.jinja_env.globals["entity_badge_config"] = get_entity_badge_config
    app.jinja_env.globals["action_badge_config"] = get_action_badge_config

    # Context processor para funções de features modulares
    @app.context_processor
    def inject_feature_helpers():
        """Disponibiliza helpers de features nos templates"""
        from flask_login import current_user

        def has_feature(feature_slug):
            """Verifica se o usuário atual tem acesso a uma feature"""
            if not current_user.is_authenticated:
                return False
            return current_user.has_feature(feature_slug)

        def get_feature_limit(feature_slug):
            """Retorna o limite de uma feature para o usuário atual"""
            if not current_user.is_authenticated:
                return 0
            return current_user.get_feature_limit(feature_slug)

        def get_monthly_credits(feature_slug):
            """Retorna os créditos mensais do usuário para uma feature"""
            if not current_user.is_authenticated:
                return 0
            return current_user.get_monthly_credits(feature_slug)

        return {
            "has_feature": has_feature,
            "get_feature_limit": get_feature_limit,
            "get_monthly_credits": get_monthly_credits,
        }

    # Registrar comandos CLI
    from app import cli

    cli.init_app(app)

    # Cache busting para arquivos estáticos (resolve problema de cache em produção)
    @app.context_processor
    def inject_static_version():
        """Adiciona função static_url que inclui hash do arquivo para cache busting"""
        _file_hashes = {}

        def static_url(filename):
            """Gera URL para arquivo estático com hash para cache busting"""
            if filename in _file_hashes:
                file_hash = _file_hashes[filename]
            else:
                filepath = os.path.join(app.static_folder, filename)
                if os.path.exists(filepath):
                    # Usa timestamp de modificação como versão
                    mtime = os.path.getmtime(filepath)
                    file_hash = str(int(mtime))
                else:
                    file_hash = "1"
                _file_hashes[filename] = file_hash

            from flask import url_for

            return f"{url_for('static', filename=filename)}?v={file_hash}"

        return {"static_url": static_url}

    return app
