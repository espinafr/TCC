from flask import render_template, abort
from app.extensions import login_required, db_manager
from app.users import bp

@bp.route('/<username>')
def view_profile(username):
    user = db_manager.get_user('id', username)
    print(username)
    if not user:
        abort(404)
    
    return render_template(
        'profile.html',
        user={
            'id': user.id,
            'username': user.username,
            'display_name': "teste",
            'bio': "bio",
            'creation_date': user.creation_date,
            'profile_image_url': "uhmhum",
            'badges': [{'name': "TESTE", 'icon_url': 'https://i.ibb.co/WN6hpqjV/imagem-2025-07-27-234935704.png'}],
            'posts': []
        },
        can_edit_profile=True
    )

@bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Aqui você pode implementar o formulário de edição de perfil
    # Por enquanto, só renderiza um placeholder
    return render_template('edit_profile.html', user=current_user)
