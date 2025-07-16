from flask import Flask, render_template, redirect, url_for, flash, session, jsonify, request
from flask_wtf import CSRFProtect
from functools import wraps
from dotenv import load_dotenv
from database import DatabaseManager, User
from email_service import EmailService
import data_sanitizer as sanitizer
from PIL import Image
from botocore.exceptions import ClientError
import boto3
import uuid
import os
import io

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

with app.app_context():
    db_manager.init_all_dbs()
    print(db_manager.save_user("admin", "admin@admin.com", "123345678", "M"))
    print(db_manager.activate_user("admin@admin.com"))

def login_required(f): # f de função original
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id' not in session:
            flash('Faça login para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 

@app.context_processor
def inject_global_variables():
    return dict (
        allowed_categories=sanitizer.ALLOWED_CATEGORIES
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', login=session.get('id'))

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
            session['id'] = user_logged_in.id
            session['username'] = user_logged_in.username
            session.permanent = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('E-mail não confirmado ou credenciais inválidas.', 'error')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    session.pop('id', None)
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
                    img = Image.open(file)

                    # Cria um buffer em memória para salvar a imagem limpa
                    img_byte_arr = io.BytesIO()

                    # Salva a imagem no buffer sem metadados EXIF.
                    if file_extension == '.jpeg' or file_extension == '.jpg':
                        img.save(img_byte_arr, format='JPEG', optimize=True)
                    elif file_extension == '.png':
                        img.save(img_byte_arr, format='PNG', optimize=True)
                    else:
                        # Para outros formatos
                        img.save(img_byte_arr, format=img.format, optimize=True)

                    img_byte_arr.seek(0) # Volta o ponteiro pro início do buffer

                    s3_client.upload_fileobj(
                        img_byte_arr, # Buffer com a imagem limpa
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

        id = db_manager.save_post(
            session['id'],
            form.titulo.data.strip(),
            form.conteudo.data.strip(),
            form.tags.data,
            form.optionaltags.data,
            image_urls_list=uploaded_files_info
        )

        if id:
            flash('Post criado com sucesso!', 'success')
        else:
            flash('Erro ao criar post. Tente novamente.', 'danger')
        return redirect(url_for('index'))
    
    return render_template('post.html', form=form)

@app.route('/post/<int:post_id>', methods=['GET'])
@login_required
def view_post(post_id):
    post = db_manager.get_post_by_id(post_id)
    if not post:
        flash('Post não encontrado.', 'error') # Considerar usar abort()
        return redirect(url_for('index'))
    
    user_id = session.get('id') # Obter o ID do usuário logado

    # Carregar contagens de likes/dislikes do post e reação do usuário
    post_likes = db_manager.count_reactions_for_post(post_id, 'like_post')
    post_dislikes = db_manager.count_reactions_for_post(post_id, 'dislike_post')
    user_post_reaction_type = None
    if user_id:
        user_post_reaction = db_manager.get_user_post_reaction(user_id, post_id)
        if user_post_reaction:
            user_post_reaction_type = user_post_reaction.type

    # Carregar comentários e suas respostas com contagens e reações do usuário
    comments_with_details = db_manager.get_comments_and_replies_for_post(post_id, user_id)

    return render_template('post_details.html',
                           post=post,
                           comments=comments_with_details, # Passa os comentários já com likes/dislikes e user_reaction
                           post_likes=post_likes,
                           post_dislikes=post_dislikes,
                           user_post_reaction=user_post_reaction_type)

# ------------- API ---------------- #
# Interações por meio de AJAX - PS: Será que devo passar tudo pro data_sanitizer?

@app.route('/api/posts/<int:post_id>/react', methods=['POST'])
@login_required
def react_to_post_api(post_id):
    user_id = session.get('id')
    reaction_type = request.json.get('reaction_type')

    if reaction_type not in ['like_post', 'dislike_post']:
        return jsonify({"success": False, "message": "Tipo de reação inválido."}), 400

    success, message = db_manager.toggle_post_reaction(user_id, post_id, reaction_type)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route('/api/comments/<int:comment_id>/react', methods=['POST'])
@login_required
def react_to_comment_api(comment_id):
    user_id = session.get('id')
    reaction_type = request.json.get('reaction_type')

    if reaction_type not in ['like_comment', 'dislike_comment']:
        return jsonify({"success": False, "message": "Tipo de reação inválido."}), 400

    success, message = db_manager.toggle_comment_reaction(user_id, comment_id, reaction_type)
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": message}), 500

@app.route('/api/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post_api(post_id):
    user_id = session.get('id')
    comment_text = request.json.get('comment_text')
    print("chego")

    if not comment_text or len(comment_text.strip()) == 0:
        return jsonify({"success": False, "message": "Comentário não pode ser vazio."}), 400
    if len(comment_text) > 300:
        return jsonify({"success": False, "message": "Comentário muito longo."}), 400

    success, result = db_manager._register_interaction(user_id, post_id, "comment_post", comment_text)
    if success:
        new_comment = db_manager.get_interaction_by_id(result) 
        return jsonify({
            "success": True, 
            "message": "Comentário adicionado com sucesso!", 
            "comment": {
                "id": new_comment.id,
                "username": new_comment.user_who_interacted.username,
                "content": new_comment.value,
                "likes": 0,
                "dislikes": 0,
                "replies": []
            }
        }), 200
    else:
        return jsonify({"success": False, "message": result}), 500

@app.route('/api/comments/<int:parent_comment_id>/reply', methods=['POST'])
@login_required
def reply_comment_api(parent_comment_id):
    user_id = session.get('id')
    reply_text = request.json.get('reply_text')

    if not reply_text or len(reply_text.strip()) == 0:
        return jsonify({"success": False, "message": "Resposta não pode ser vazia."}), 400
    if len(reply_text) > 300:
        return jsonify({"success": False, "message": "Resposta muito longa."}), 400
    
    success, result = db_manager.register_reply_to_comment(user_id, parent_comment_id, reply_text)
    if success:
        new_reply_id = result
        new_reply = db_manager.get_interaction_by_id(new_reply_id) 
        return jsonify({
            "success": True, 
            "message": "Resposta adicionada com sucesso!", 
            "reply": {
                "id": new_reply.id,
                "username": new_reply.user_who_interacted.username,
                "content": new_reply.value,
                "likes": 0,
                "dislikes": 0
            }
        }), 200
    else:
        return jsonify({"success": False, "message": result}), 500

@app.route('/api/posts/<int:post_id>/counts', methods=['GET'])
@login_required
def get_post_counts_api(post_id):
    likes_count = db_manager.count_reactions_for_post(post_id, 'like_post')
    dislikes_count = db_manager.count_reactions_for_post(post_id, 'dislike_post')
    
    # Opcional: Obter o estado de reação do usuário logado
    user_id = session.get('id')
    user_reaction = None
    if user_id:
        user_reaction_obj = db_manager.get_user_post_reaction(user_id, post_id)
        if user_reaction_obj:
            user_reaction = user_reaction_obj.type # 'like_post' ou 'dislike_post'

    return jsonify({
        "success": True, 
        "likes": likes_count, 
        "dislikes": dislikes_count,
        "user_reaction": user_reaction # Envia a reação do usuário
    }), 200

@app.route('/api/comments/<int:comment_id>/counts', methods=['GET'])
@login_required
def get_comment_counts_api(comment_id):
    likes_count = db_manager.count_reactions_for_comment(comment_id, 'like_comment')
    dislikes_count = db_manager.count_reactions_for_comment(comment_id, 'dislike_comment')

    user_id = session.get('id')
    user_reaction = None
    if user_id:
        user_reaction_obj = db_manager.get_user_comment_reaction(user_id, comment_id)
        if user_reaction_obj:
            user_reaction = user_reaction_obj.type # 'like_comment' ou 'dislike_comment'

    return jsonify({
        "success": True, 
        "likes": likes_count, 
        "dislikes": dislikes_count,
        "user_reaction": user_reaction
    }), 200

# Rota para buscar comentários (útil para adicionar dinamicamente ou recarregar)
@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
@login_required
def get_post_comments_api(post_id):
    user_id = session.get('id') # Pega o ID do usuário para obter as reações dele
    comments_data = db_manager.get_comments_and_replies_for_post(post_id, user_id)
    
    return jsonify({"success": True, "comments": comments_data}), 200

if __name__ == '__main__':
    app.run(debug=True)