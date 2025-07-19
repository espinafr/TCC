from flask import Flask
from flask_wtf import CSRFProtect
import app.data_sanitizer as sanitizer
from app.extensions import db_manager, email_service, mail, s3
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="public")
    app.config.from_object(config_class)
    
    # Iniciando extensões
    mail.init_app(app)
    email_service.init_app(app)
    s3.init_app(app)

    # Habilitando proteção CSRF
    csrf = CSRFProtect(app)

    with app.app_context():
        db_manager.init_all_dbs()
        print(db_manager.save_user("admin", "admin@admin.com", "123345678", "M"))
        print(db_manager.activate_user("admin@admin.com"))

    @app.context_processor
    def inject_global_variables():
        return dict (
            allowed_categories=sanitizer.ALLOWED_CATEGORIES
        )

    # Registrando blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.email import bp as email_bp
    app.register_blueprint(email_bp, url_prefix='/email')

    from app.authentication import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.posts import bp as posts_bp
    app.register_blueprint(posts_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    @app.route("/oiiii")
    def test_page():
        return "<h1>oiiiii uwu</h1>"
    
    return app
