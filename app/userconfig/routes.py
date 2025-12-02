from flask import render_template, jsonify, request, session
from app.extensions import db_manager, login_required
from app.userconfig import bp


@bp.route('/')
@login_required
def mainconfigpage():
    return render_template('configs.html')


@bp.route('/account_info', methods=['GET'])
@login_required
def account_info():
    # Return basic account info. db_manager.get_user_details should return a user object
    user = db_manager.get_user("id", session.get('id'))
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404

    return jsonify({
        'success': True,
        'email': user.email,
        'created_at': str(user.creation_date),
        'username': user.username
    }), 200


@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json() or request.form
    current = data.get('current_password')
    new1 = data.get('new_password')
    new2 = data.get('new_password_confirm')

    if not current or not new1 or not new2:
        return jsonify({'success': False, 'message': 'Campos incompletos.'}), 400
    if new1 != new2:
        return jsonify({'success': False, 'message': 'As senhas não conferem.'}), 400

    success, msg = db_manager.change_user_password(session.get('id'), current, new1)
    if success:
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso.'}), 200
    else:
        return jsonify({'success': False, 'message': msg or 'Senha atual incorreta ou erro interno.'}), 400


@bp.route('/deactivate', methods=['POST'])
@login_required
def deactivate():
    # Placeholder: mark account as deactivated
    success, msg = db_manager.deactivate_user(session.get('id'))
    if success:
        # also log out
        session.pop('id', None)
        session.pop('username', None)
        return jsonify({'success': True, 'message': 'Conta desativada. Você foi deslogado.'})
    else:
        # Caso já estivesse desativada, retornar 400; para erro interno, retornar 500
        if msg == 'Conta já está desativada.':
            return jsonify({'success': False, 'message': msg}), 400
        elif msg:
            return jsonify({'success': False, 'message': msg}), 500
        else:
            return jsonify({'success': False, 'message': 'Erro ao desativar conta.'}), 500