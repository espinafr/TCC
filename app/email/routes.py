from flask import redirect, url_for, flash
from app.extensions import db_manager, email_service
from app.email import bp

@bp.route('/confirmar/<token>')
def confirm_email(token):
    success, email_or_error = email_service.verify_token(token)
    if success:
        user = db_manager.activate_user(email_or_error)
        if user:
            flash('E-mail confirmado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('authentication.login'))
        else:
            flash('Erro ao ativar conta ou e-mail já ativado.', 'error')
            return redirect(url_for('main.index'))
    else:
        flash(email_or_error, 'error')
    return redirect(url_for('main.index'))
