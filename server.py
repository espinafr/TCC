from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import CSRFProtect
from functools import wraps
from dotenv import load_dotenv
import os
from database import DatabaseManager
from email_service import EmailService
from data_sanitizer import Sanitizer

app = Flask(__name__, template_folder="views", static_folder="public")
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 2678400 # 31 dias em segundos

# Habilitando proteção CSRF
csrf = CSRFProtect(app)

# Inicializando serviços
db = DatabaseManager('users.db')
email_service = EmailService(app)
sanitizer = Sanitizer()

# Inicializando bancos de dados
db.init_users_db()
db.init_missions_db()

def getValidationErrors(validationErrs):
    if len(validationErrs) > 0:
            [flash(erro, 'error') for erro in validationErrs]
            return True
    return False

def login_required(f): # f de função original
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'login' not in session:
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = sanitizer.RegistrationForm()
    if form.validate_on_submit():
        data = {
            'username': request.form['username'],
            'email': request.form['email'],
            'password': request.form['password'],
            'gender': request.form['gender'] 
        }
        
        #if getValidationErrors(sanitizer.validate_registration(data)): return redirect(url_for('register'))
        
        success, error = db.save_user(data['username'], data['email'], data['password'], data['gender'])
        if not success:
            flash(error, 'error')
            return redirect(url_for('register'))

        token = email_service.generate_token(data['email'])
        confirm_url = url_for('confirm_email', token=token, _external=True)
        success, error = email_service.send_confirmation_email(data['email'], data['username'], confirm_url)
        if success:
            flash('Um e-mail de confirmação foi enviado!', 'success')
        else:
            flash(f'Erro ao enviar e-mail: {error}', 'error')

        return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    success, result = email_service.verify_token(token)
    if success:
        db.activate_user(result)
        flash('E-mail confirmado com sucesso! Faça login para continuar.', 'success')
    else:
        flash(result, 'error')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = sanitizer.LoginForm()
    if form.validate_on_submit():
        active = db.logto_user(form.login.data, form.password.data['password'], 'email' if '@' in form.login.data else 'username')
        if active == 1:
            session['login'] = form.login.data
            session.permanent = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('login'))
        else:
            flash('E-mail não confirmado ou credenciais inválidas.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('login', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('login'))

@app.route('/missions')
@login_required
def dashboard():
    return render_template('missions.html')

@app.route('/mission/<user_id>')
def show_mission(user_id):
    # Exemplo simplificado, integrar com preferências do usuário
    missions = db.get_mission(child_age=10, interests=['criatividade'], available_time=30)
    if missions:
        import random
        mission_data = random.choice(missions)
        return render_template('mission.html', mission={'mission': mission_data[0], 'duration': mission_data[1]})
    flash('Nenhuma missão encontrada.', 'error')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)