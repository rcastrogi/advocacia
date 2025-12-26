import os

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # Database configuration
    DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///" + os.path.join(
        basedir, "app.db"
    )

    # Fix for Heroku/Render postgres:// URLs (SQLAlchemy 1.4+ requires postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL connection pool settings (only for PostgreSQL)
    if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith(
        "postgres://"
    ):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,  # Verify connection before using
            "pool_recycle": 300,  # Recycle connections every 5 minutes
            "pool_size": 5,  # Number of connections to keep
            "max_overflow": 10,  # Extra connections when pool is full
        }
    else:
        # SQLite doesn't support connection pooling
        SQLALCHEMY_ENGINE_OPTIONS = {}

    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # CSRF Protection - Disabled in development for easier testing
    WTF_CSRF_ENABLED = False

    # Mail settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "noreply@advocaciasaas.com"
    )

    # CEP API
    CEP_API_URL = "https://viacep.com.br/ws/{}/json/"

    # Mercado Pago Payment Settings (Brasil)
    MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN")
    MERCADOPAGO_PUBLIC_KEY = os.environ.get("MERCADOPAGO_PUBLIC_KEY")
    MERCADOPAGO_WEBHOOK_SECRET = os.environ.get("MERCADOPAGO_WEBHOOK_SECRET")

    # Sentry Error Tracking
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # Redis Configuration
    REDIS_URL = os.environ.get("REDIS_URL")
    REDIS_CACHE_DB = int(os.environ.get("REDIS_CACHE_DB", "0"))  # DB para cache
    REDIS_RATELIMIT_DB = int(
        os.environ.get("REDIS_RATELIMIT_DB", "1")
    )  # DB para rate limiting
    REDIS_SESSION_DB = int(
        os.environ.get("REDIS_SESSION_DB", "2")
    )  # DB para sessões (futuro)

    # Cache settings
    CACHE_DEFAULT_TIMEOUT = int(
        os.environ.get("CACHE_DEFAULT_TIMEOUT", "300")
    )  # 5 minutos
    CACHE_KEY_PREFIX = os.environ.get("CACHE_KEY_PREFIX", "petitio")

    # OpenAI API
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    # Environment settings
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ["true", "on", "1"]
    ENV = os.environ.get("FLASK_ENV", "production")

    # Security settings
    FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "False").lower() in ["true", "on", "1"]

    # Trial settings
    DEFAULT_TRIAL_DAYS = int(os.environ.get("DEFAULT_TRIAL_DAYS", 3))
