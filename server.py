from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import CSRFProtect
from functools import wraps
from dotenv import load_dotenv
from database import DatabaseManager, User
from recommendation_service import RecommendationService
from email_service import EmailService
import data_sanitizer as sanitizer
from botocore.exceptions import ClientError
import boto3
import uuid
import os

# TAILWIND NÃO PODE SER USADO EM PRODUÇÃO, LEMBRAR DE MUDAR ISSO!!!

app = Flask(__name__, template_folder="views", static_folder="public")
load_dotenv()

# Configurações flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 5 * 10 * 1024 * 1024
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 2678400 # 31 dias em segundos

# AWS S3
app.config['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
app.config['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
app.config['AWS_REGION'] = os.getenv('AWS_REGION')
app.config['S3_BUCKET_NAME'] = os.getenv('S3_BUCKET_NAME')

s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
    region_name=app.config['AWS_REGION']
)

# Habilitando proteção CSRF
csrf = CSRFProtect(app)

# Inicializando serviços
db_manager  = DatabaseManager()
email_service = EmailService(app)
recommendation_service = RecommendationService(db_manager)

with app.app_context():
    db_manager.init_all_dbs()

def login_required(f): # f de função original
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'login' not in session:
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 

@app.context_processor
def inject_global_variables():
    return dict (
        allowed_categories= sanitizer.ALLOWED_CATEGORIES,
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', login=session.get('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = sanitizer.RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        gender = form.gender.data
        
        is_email_available, email_msg = db_manager.check_user_activation('email', email)
        if not is_email_available:
            flash(email_msg, 'error')
            return redirect(url_for('register'))

        is_username_available, username_msg = db_manager.check_user_activation('username', username)
        if not is_username_available:
            flash(username_msg, 'error')
            return redirect(url_for('register'))

        success, error_message = db_manager.save_user(username, email, password, gender)
        
        if not success:
            flash(error_message, 'error')
            return redirect(url_for('register'))

        token = email_service.generate_token(email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        success, error = email_service.send_confirmation_email(email, username, confirm_url)
        if success:
            flash('Um e-mail de confirmação foi enviado!', 'success')
        else:
            flash(f'Erro ao enviar e-mail: {error}', 'error')

        return redirect(url_for('register'))
    
    return render_template('register.html', form=form)

@app.route('/confirm/<token>')
def confirm_email(token):
    success, result = email_service.verify_token(token)
    success, email_or_error = email_service.verify_token(token)
    if success:
        if db_manager.activate_user(email_or_error):
            flash('E-mail confirmado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Erro ao ativar conta ou e-mail já ativado.', 'error')
            return redirect(url_for('index'))
    else:
        flash(email_or_error, 'error')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = sanitizer.LoginForm()
    if form.validate_on_submit():
        user_logged_in = db_manager.logto_user(form.login.data, form.password.data, 'email' if '@' in form.login.data else 'username')
        
        if user_logged_in:
            session['login'] = user_logged_in.email
            session.permanent = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail não confirmado ou credenciais inválidas.', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    session.pop('login', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = sanitizer.PostForm()
    if form.validate_on_submit():
        uploaded_files_info = []
        
        for file in form.images.data:
            if file and file.filename: # Verificar se um arquivo foi realmente enviado para este campo
                try:
                    file_extension = os.path.splitext(file.filename)[1]
                    unique_filename = str(uuid.uuid4()) + file_extension
                    s3_client.upload_fileobj(
                        file,
                        app.config['S3_BUCKET_NAME'],
                        f'public/{unique_filename}',
                        ExtraArgs={
                            'ContentType': file.content_type
                        }
                    )

                    file_url = f"https://{app.config['S3_BUCKET_NAME']}.s3.{app.config['AWS_REGION']}.amazonaws.com/public/{unique_filename}"
                    uploaded_files_info.append(file_url)
                except ClientError as e:
                    flash(f'Erro ao fazer upload para o S3 para {file.filename}: {e}', 'danger')
                    print(f"Erro S3: {e}")
                except Exception as e:
                    flash(f'Erro inesperado ao processar {file.filename}: {e}', 'danger')
                    print(f"Erro geral: {e}")

        post_id = db_manager.save_post(
            session['login'],
            form.titulo.data,
            form.conteudo.data,
            form.tags.data,
            form.optionaltags.data,
            image_urls_list=uploaded_files_info
        )

        if post_id:
            flash('Post criado com sucesso!', 'success')
        else:
            flash('Erro ao criar post. Tente novamente.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('post.html', form=form)

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    # Evitar curtidas duplicadas
    interactions = db_manager.get_user_interactions(session['login'], interaction_type='like')
    if not any(i['post_id'] == post_id and i['type'] == 'like' for i in interactions):
        db_manager.register_interaction(session['login'], post_id, 'like')
        flash('Post curtido!', 'success')
    return redirect(url_for('index'))

@app.route('/view/<int:post_id>', methods=['GET'])
@login_required
def view_post(post_id):
    db_manager.register_interaction(session['login'], post_id, 'view')
    post = db_manager.get_post_by_id(post_id)
    
    if post:
        return render_template('post_details.html', post=post)
    else:
        flash('Post não encontrado.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)