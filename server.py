from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import CSRFProtect
from functools import wraps
from dotenv import load_dotenv
import os
from database import DatabaseManager
from email_service import EmailService
from forms import PostForm
import data_sanitizer as sanitizer
import numpy as np
from collections import defaultdict

# TAILWIND NÃO PODE SER USADO EM PRODUÇÃO, LEMBRAR DE MUDAR ISSO!!!

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

def calculate_user_similarity(interactions):
    # Criar matriz usuário-post
    user_posts = defaultdict(lambda: defaultdict(float))
    users = set()
    posts = set()
    
    for interaction in interactions:
        email = interaction['email']
        post_id = interaction['post_id']
        interaction_type = interaction['type']
        users.add(email)
        posts.add(post_id)
        # Atribuir peso às interações
        if interaction_type == 'like':
            user_posts[email][post_id] = 1.0
        elif interaction_type == 'view':
            user_posts[email][post_id] = 0.5
    
    users = list(users)
    posts = list(posts)
    n_users = len(users)
    n_posts = len(posts)
    
    # Construir matriz numpy
    matrix = np.zeros((n_users, n_posts))
    user_index = {user: i for i, user in enumerate(users)}
    post_index = {post: i for i, post in enumerate(posts)}
    
    for email in user_posts:
        for post_id, score in user_posts[email].data.items():
            matrix[user_index[email]][post_index[post_id]] = score
    
    # Calcular similaridade de cosseno
    norms = np.sqrt(sum(matrix ** 2, axis=1))
    norms[norms == 0] = 1  # Evitar divisão por zero
    normalized_matrix = matrix / norms[:, None]
    similarity_matrix = normalized_matrix @ normalized_matrix.T
    
    return similarity_matrix, user_index, post_index, users, posts

def recommend_posts(email, db, k_users=5, n_recommend=10):
    # Obter todas as interações
    interactions = db.get_all_interactions()
    user_interactions = db.get_user_interactions(email)
    liked_posts = {i['post_id'] for i in user_interactions if i['type'] == 'like'}
    viewed_posts = {i['post_id'] for i in user_interactions if i['type'] == 'view'}
    
    # Calcular similaridade
    sim_matrix, user_index, post_index, users, posts = calculate_user_similarity(interactions)
    
    if email not in user_index:
        return []  # Fallback para novos usuários
    
    user_idx = user_index[email]
    similarities = sim_matrix[user_idx]
    
    # Selecionar K usuários mais semelhantes
    similar_users_idx = np.argsort(similarities)[::-1][1:k_users+1]  # Exclui o próprio usuário
    similar_users = [users[idx] for idx in similar_users_idx]
    
    # Coletar posts curtidos pelos usuários semelhantes
    recommended_posts = defaultdict(float)
    for sim_user in similar_users:
        sim_user_interactions = [i for i in interactions if i['email'] == sim_user]
        for interaction in sim_user_interactions:
            post_id = interaction['post_id']
            if post_id not in liked_posts and post_id not in viewed_posts:
                if interaction['type'] == 'like':
                    recommended_posts[post_id] += similarities[user_index[sim_user]]
    
    # Ordenar posts por pontuação
    recommended = sorted(recommended_posts.items(), key=lambda x: x[1], reverse=True)[:n_recommend]
    return [db.get_post_by_id(post_id) for post_id, _ in recommended]

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', login=session.get('login'))

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
    
    return render_template('register.html', form=form)

@app.route('/confirm/<token>')
def confirm_email(token):
    success, result = email_service.verify_token(token)
    if success:
        db.activate_user(result)
        flash('E-mail confirmado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login'))
    else:
        flash(result, 'error')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = sanitizer.LoginForm()
    if form.validate_on_submit():
        active = db.logto_user(form.login.data, form.password.data, 'email' if '@' in form.login.data else 'username')
        if active == 1:
            session['login'] = form.login.data
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

@app.route('/post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        db = DatabaseManager('users.db')
        post_id = db.save_post(
            session['user_email'],
            form.title.data,
            form.content.data,
            form.tags.data
        )
        flash('Post criado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('post.html', form=form)

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    db = DatabaseManager('users.db')
    # Evitar curtidas duplicadas
    interactions = db.get_user_interactions(session['user_email'])
    if not any(i['post_id'] == post_id and i['type'] == 'like' for i in interactions):
        db.register_interaction(session['user_email'], post_id, 'like')
        flash('Post curtido!', 'success')
    return redirect(url_for('index'))

@app.route('/view/<int:post_id>', methods=['GET'])
@login_required
def view_post(post_id):
    db = DatabaseManager('users.db')
    db.register_interaction(session['user_email'], post_id, 'view')
    post = db.get_post_by_id(post_id)
    return render_template('post_detail.html', post=post)

if __name__ == '__main__':
    app.run(debug=True)