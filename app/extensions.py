from flask import session, redirect, url_for, flash, current_app
from functools import wraps
from app.database import DatabaseManager
from flask_mail import Mail
from app.email_service import EmailService
import boto3

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id' not in session:
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 

s3 = s3Handler()