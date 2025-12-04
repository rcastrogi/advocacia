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

    # PostgreSQL connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,  # Verify connection before using
        "pool_recycle": 300,  # Recycle connections every 5 minutes
        "pool_size": 5,  # Number of connections to keep
        "max_overflow": 10,  # Extra connections when pool is full
    }

    UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # CSRF Protection - Disabled in development for easier testing
    WTF_CSRF_ENABLED = False

    # Mail settings (for future implementation)
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or 587)
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    # CEP API
    CEP_API_URL = "https://viacep.com.br/ws/{}/json/"

    # Stripe Payment Settings
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
    STRIPE_SUCCESS_URL = (
        os.environ.get("STRIPE_SUCCESS_URL") or "http://localhost:5000/checkout/success"
    )
    STRIPE_CANCEL_URL = (
        os.environ.get("STRIPE_CANCEL_URL") or "http://localhost:5000/checkout/cancel"
    )
