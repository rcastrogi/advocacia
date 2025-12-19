import os

from config import Config
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_caching import Cache

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
cache = Cache()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure JSON and response encoding
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"

    # Initialize Sentry for error tracking
    if app.config.get('SENTRY_DSN'):
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        
        sentry_sdk.init(
            dsn=app.config['SENTRY_DSN'],
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            environment=app.config.get('ENV', 'production')
        )

    # Initialize security headers (HTTPS, HSTS, CSP)
    if not app.config.get('DEBUG'):
        Talisman(app, 
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            content_security_policy={
                'default-src': ["'self'"],
                'script-src': [
                    "'self'", 
                    "'unsafe-inline'",  # Necessário para Alpine.js inline
                    "cdn.jsdelivr.net",
                    "unpkg.com",
                    "cdnjs.cloudflare.com"
                ],
                'style-src': [
                    "'self'", 
                    "'unsafe-inline'",
                    "cdn.jsdelivr.net",
                    "cdnjs.cloudflare.com",
                    "fonts.googleapis.com"
                ],
                'font-src': [
                    "'self'",
                    "fonts.gstatic.com",
                    "cdnjs.cloudflare.com"
                ],
                'img-src': ["'self'", "data:", "https:"],
                'connect-src': ["'self'"]
            }
        )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # Initialize cache
    cache.init_app(app, config={
        'CACHE_TYPE': 'redis' if app.config.get('REDIS_URL') else 'simple',
        'CACHE_REDIS_URL': app.config.get('REDIS_URL'),
        'CACHE_DEFAULT_TIMEOUT': 300
    })

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

    from app.checkout import bp as checkout_bp

    app.register_blueprint(checkout_bp, url_prefix="/checkout")

    from app.ai import ai_bp

    app.register_blueprint(ai_bp)

    from app.admin import bp as admin_bp

    app.register_blueprint(admin_bp)

    return app
