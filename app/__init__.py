from flask import Flask
from .models.db import init_db
from .routes.auth import auth_bp
from .routes.pages import pages_bp
from .routes.profile import profile_bp
from .routes.search import search_bp
from .routes.admin import admin_bp
import os


def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')

    is_production = os.environ.get('RENDER') or os.environ.get('PRODUCTION')
    app.config.update(
        SESSION_COOKIE_HTTPONLY   = True,
        SESSION_COOKIE_SECURE     = bool(is_production),
        SESSION_COOKIE_SAMESITE   = 'Lax',
        SESSION_COOKIE_NAME       = 'pdfh_session',
        PERMANENT_SESSION_LIFETIME= 86400 * 30,
    )

    db_path = os.environ.get('DATABASE_PATH', 'instance/app.db')
    app.config['DATABASE_PATH'] = db_path

    with app.app_context():
        init_db()

    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp,    url_prefix='/api')
    app.register_blueprint(profile_bp, url_prefix='/api')
    app.register_blueprint(search_bp,  url_prefix='/api')
    app.register_blueprint(admin_bp)

    return app
