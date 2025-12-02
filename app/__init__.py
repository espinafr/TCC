from flask import Flask, session, send_from_directory, flash, redirect, url_for
from flask_wtf import CSRFProtect
from app.extensions import db_manager, email_service, mail, s3
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, template_folder="templates", static_folder="public")
    app.config.from_object(config_class)
    
    # Iniciando extensões
    mail.init_app(app)
    email_service.init_app(app)
    s3.init_app(app)
    # Limiter is optional and not initialized by default
    # If you need to enable it, uncomment and configure a storage backend in app/extensions.py and initialize it here.
    # Example:
    # from app.extensions import limiter
    # limiter.init_app(app)
    # Habilitar ProxyFix se a aplicação estiver atrás de um proxy reverso na produção
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # Habilitar Talisman para cabeçalhos de segurança (HSTS, CSP)
    talisman = Talisman()
    talisman.init_app(app, content_security_policy={
        'default-src': ["'self'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'script-src': ["'self'", 'https:', "'unsafe-inline'"],
        'style-src': ["'self'", 'https:', "'unsafe-inline'"]
    })

    # Habilitando proteção CSRF
    csrf = CSRFProtect(app)

    with app.app_context():
        db_manager.init_all_dbs()

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
    
    from app.userconfig import bp as userconfig
    app.register_blueprint(userconfig, url_prefix="/configuracoes")

    # Registrando error handlers para códigos HTTP
    @app.errorhandler(401)
    def unauthorized_error(error):
        flash('Faça login para acessar esta página.', 'warning')
        return redirect(url_for('authentication.login'))

    @app.errorhandler(403)
    def forbidden_error(error):
        flash('Você não tem permissão para acessar esta página.', 'error')
        return redirect(url_for('main.index'))
    
    @app.errorhandler(404)
    def forbidden_error(error):
        flash('Página não encontrada!', 'error')
        return redirect(url_for('main.index'))

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt")

    @app.route("/recursos")
    def recursos():
        flash('Página em desenvolvimento!', 'error')
        return redirect(url_for('main.index'))
    
    @app.route("/dicas")
    def dicas():
        flash('Página em desenvolvimento!', 'error')
        return redirect(url_for('main.index'))
    
    @app.route("/missoes")
    def missiooon():
        flash('Página em desenvolvimento!', 'error')
        return redirect(url_for('main.index'))
    
    @app.route("/perfil")
    def perff():
        flash('Página em desenvolvimento!', 'error')
        return redirect(url_for('main.index'))

    @app.route("/segredoultrasecreto")
    def test_page():
        return "<h1>oiiiii !!</h1>"
    
    return app

