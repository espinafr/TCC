from flask import render_template, redirect, url_for, flash, session
from app.extensions import db_manager, login_required, email_service
import app.data_sanitizer as sanitizer
from app.authentication import bp

@bp.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('authentication.register'))

        is_username_available, username_msg = db_manager.check_user_activation('username', username)
        if not is_username_available:
            flash(username_msg, 'error')
            return redirect(url_for('authentication.register'))

        success, error_message = db_manager.save_user(username, email, password, gender)
        
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
        user_logged_in = db_manager.logto_user(form.login.data, form.password.data, 'email' if '@' in form.login.data else 'username')
        
        if user_logged_in:
            session['id'] = user_logged_in.id
            session['username'] = user_logged_in.username
            session.permanent = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('E-mail não confirmado ou credenciais inválidas.', 'error')
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    session.pop('id', None)
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('authentication.login'))