from flask import render_template, redirect, url_for, flash, session, jsonify, request
from app.extensions import db_manager, login_required, email_service
import app.data_sanitizer as sanitizer
from app.authentication import bp

def _process_login_attempt_and_session(form_obj):
    login_type = 'email' if '@' in form_obj.login.data else 'username'
    user_logged_in = db_manager.logto_user(form_obj.login.data, form_obj.password.data, login_type)

    if user_logged_in:
        session['id'] = user_logged_in.id
        session['username'] = user_logged_in.username
        session.permanent = True
        return True, user_logged_in
    else:
        return False, 'E-mail não confirmado ou credenciais inválidas.'

@bp.route('/registrar', methods=['GET', 'POST'])
def register():
    form = sanitizer.RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        is_email_available, email_msg = db_manager.check_user_activation('email', email)
        if not is_email_available:
            flash(email_msg, 'error')
            return redirect(url_for('authentication.register'))

        is_username_available, username_msg = db_manager.check_user_activation('username', username)
        if not is_username_available:
            flash(username_msg, 'error')
            return redirect(url_for('authentication.register'))

        success, error_message = db_manager.save_user(username, email, password)
        
        if not success:
            flash(error_message, 'error')
            return redirect(url_for('authentication.register'))

        token = email_service.generate_token(email)
        confirm_url = url_for('email.confirm_email', token=token, _external=True)
        success, error = email_service.send_confirmation_email(email, username, confirm_url)
        if success:
            flash('Um e-mail de confirmação foi enviado!', 'success')
        else:
            flash(f'Erro ao enviar e-mail: {error}', 'error')

        return redirect(url_for('authentication.register'))
    
    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = sanitizer.LoginForm()
    if form.validate_on_submit():
        success, result = _process_login_attempt_and_session(form)
        if success:
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash(result, 'error')
    return render_template('login.html', form=form)

@bp.route('/login_ajax', methods=['POST'])
def login_ajax():
    form = sanitizer.LoginForm()

    if request.is_json:
        # Se a requisição for JSON, os dados NÃO virão em request.form
        # Precisamos populá-los manualmente do request.get_json()
        json_data = request.get_json()
        if json_data:
            form.login.data = json_data.get('login')
            form.password.data = json_data.get('password')
        else:
            # Caso o JSON esteja vazio ou malformado
            return jsonify({'success': False, 'message': 'Corpo da requisição JSON inválido ou vazio.'}), 400
    else:
        # Se a requisição não for JSON (e.g., FormData ou application/x-www-form-urlencoded),
        # o Flask-WTF já preenche o formulário automaticamente a partir de request.form
        # Isso significa que form = LoginForm() já faria a mágica se fosse um form submit :D.
        pass

    if form.validate():
        success, result = _process_login_attempt_and_session(form)
        if success:
            return jsonify({'success': True, 'message': 'Login bem-sucedido!', 'username': result.username}), 200
        else:
            return jsonify({'success': False, 'message': result}), 401
    else:
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'}), 400
    

@bp.route('/logout')
@login_required
def logout():
    session.pop('id', None)
    session.pop('username', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('.login'))