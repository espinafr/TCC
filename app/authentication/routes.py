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
        if user_logged_in.power > 0:
            session['power'] = user_logged_in.power
        session.permanent = True
        return True, user_logged_in
    else:
        return False, 'E-mail não confirmado ou credenciais inválidas.'

@bp.route('/registrar', methods=['GET'])
def register():
    return render_template('register.html')

@bp.route('/register_ajax', methods=['POST'])
def register_ajax():
    form = sanitizer.RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        
        is_email_available, email_msg = db_manager.check_user_activation('email', email)
        if not is_email_available:
            return jsonify({"success": False, 'message': email_msg}), 409

        is_username_available, username_msg = db_manager.check_user_activation('username', username)
        if not is_username_available:
            return jsonify({"success": False, 'message': username_msg}), 409

        success, error_message = db_manager.save_user(username, email, password)
        
        if not success:
            return jsonify({"success": False, 'message': error_message}), 500

        token = email_service.generate_token(email)
        confirm_url = url_for('email.confirm_email', token=token, _external=True)
        success, error = email_service.send_confirmation_email(email, username, confirm_url)
        if success:
            flash(f'Um e-mail de confirmação foi enviado para {email}!\nResponda em até 1 (uma) hora.', 'success')
            return jsonify({"success": True, 'redirect_url': url_for('authentication.login')}), 200
        else:
            return jsonify({"success": False, 'message': f"Erro interno ao enviar email: {error}"}), 500
    else:
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'})

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
        json_data = request.get_json()
        if json_data:
            form.login.data = json_data.get('login')
            form.password.data = json_data.get('password')
        else:
            return jsonify({'success': False, 'message': 'Corpo da requisição JSON inválido ou vazio.'}), 400

    if form.validate():
        success, result = _process_login_attempt_and_session(form)
        if success:
            return jsonify({'success': True, 'message': 'Login bem-sucedido!', 'username': result.username}), 200
        else:
            return jsonify({'success': False, 'message': result}), 401
    else:
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'}), 400
    

@bp.route('/sair')
@login_required
def logout():
    session.pop('id', None)
    session.pop('username', None)
    session.pop('power', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('.login'))