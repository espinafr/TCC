from flask import session, redirect, url_for, flash, current_app, g
from functools import wraps
from datetime import datetime
from app.database import DatabaseManager, User, ModerationHistory
from flask_mail import Mail
from app.email_service import EmailService
import boto3
import json

# Inicializando serviços
mail = Mail()
email_service = EmailService()
db_manager  = DatabaseManager()

class s3Handler:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.client = boto3.client(
            's3',
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=app.config['AWS_REGION']
        )

def load_logged_in_user():
    """
    Carrega o usuário logado e verifica status de moderação.
    Armazena o usuário em g.user para acesso fácil.
    """
    user_id = session.get('id')
    g.user = None
    g.is_banned_or_deactivated = False

    if user_id:
        with db_manager.get_db() as db_session:
            user = db_session.query(User).filter_by(id=user_id).first()
            if user:
                g.user = user
                
                # Verificar por banimentos ou desativações ativas
                active_moderations = db_session.query(ModerationHistory).filter(
                    ModerationHistory.user_id == user_id,
                    ModerationHistory.is_active == True,
                    ModerationHistory.end_date > datetime.now(), # A moderação ainda está ativa
                    ModerationHistory.action_type.in_(['ban', 'deactivation'])
                ).first() # Basta encontrar uma para saber que está afetado

                if active_moderations:
                    g.is_banned_or_deactivated = True
            else:
                # Se o ID na sessão não corresponde a um usuário, limpa a sessão
                session.clear()
    return g.user


def login_required(f):
    """
    Decorator para rotas que exigem que o usuário esteja logado
    e não tenha banimento/desativação ativa.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        load_logged_in_user() # Carrega o usuário e verifica status
        
        if not g.user:
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('authentication.login'))
        
        if g.is_banned_or_deactivated:
            flash('Sua conta está inativa devido a uma ação de moderação. Por favor, entre em contato com o suporte.', 'error')
            session.clear() # Opcional: limpar a sessão se o usuário estiver banido/desativado
            return redirect(url_for('authentication.login')) # Ou uma página específica de erro/informação
            
        return f(*args, **kwargs)
    return decorated_function

def power_required(required_power=1):
    """
    Decorator para rotas que exigem que o usuário esteja logado,
    não tenha banimento/desativação e tenha um nível de 'power' mínimo.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            load_logged_in_user() # Carrega o usuário e verifica status

            if not g.user:
                flash('Faça login para acessar esta página.', 'error')
                return redirect(url_for('authentication.login'))
            
            if g.is_banned_or_deactivated:
                flash('Sua conta está inativa devido a uma ação de moderação. Por favor, entre em contato com o suporte.', 'error')
                session.clear()
                return redirect(url_for('authentication.login'))

            if g.user.power < required_power:
                flash(f'Você não tem permissão para acessar esta página. É necessário um nível de acesso {required_power} ou superior.', 'error')
                return redirect(url_for('main.index')) # Redirecione para uma página padrão ou de erro

            return f(*args, **kwargs)
        return decorated_function
    return decorator

    return g.user

s3 = s3Handler()