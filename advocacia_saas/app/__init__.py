import os

from config import Config
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure JSON and response encoding
    app.config["JSON_AS_ASCII"] = False
    app.config["JSONIFY_MIMETYPE"] = "application/json; charset=utf-8"

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

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
