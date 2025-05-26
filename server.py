from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import os
from database import DatabaseManager
from email_service import EmailService

app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')

# Inicializar serviços
db = DatabaseManager('users.db')
email_service = EmailService(app)

# Inicializar bancos de dados
db.init_users_db()
db.init_missions_db()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        gender = request.form['gender']
        
        success, error = db.save_user(email, password)
        if not success:
            flash(error, 'error')
            return redirect(url_for('register'))
        
        token = email_service.generate_token(email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        success, error = email_service.send_confirmation_email(email, confirm_url)
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
        db.confirm_user(result)
        flash('E-mail confirmado com sucesso! Faça login para continuar.', 'success')
    else:
        flash(result, 'error')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirmed = db.check_user(email, password)
        if confirmed == 1:
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('E-mail não confirmado ou credenciais inválidas.', 'error')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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