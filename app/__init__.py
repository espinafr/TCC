from flask import Flask, session, render_template, flash, redirect, url_for
from flask_wtf import CSRFProtect
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
        print(db_manager.save_user("admin", "admin@admin.com", "123345678", "3"))
        print(db_manager.activate_user("admin@admin.com"))
        #db_manager.create_user_profile(1)

    @app.context_processor
    def inject_global_variables():
        return dict (
            logged_in=session.get('id')
        )

    # Registrando blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.email import bp as email_bp
    app.register_blueprint(email_bp, url_prefix='/email')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/adm')

    from app.authentication import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.posts import bp as posts_bp
    app.register_blueprint(posts_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix="/usuario")

    # Registrando error handlers para códigos HTTP
    @app.errorhandler(401)
    def unauthorized_error(error):
        flash('Faça login para acessar esta página.', 'warning')
        return redirect(url_for('authentication.login'))

    @app.errorhandler(403)
    def forbidden_error(error):
        flash('Você não tem permissão para acessar esta página.', 'error')
        return redirect(url_for('main.index'))

    @app.route("/oiiii")
    def test_page():
        return "<h1>oiiiii uwu</h1>"
    
    return app
