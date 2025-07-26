from flask import request, jsonify, session
from app.extensions import login_required, db_manager
from app.data_sanitizer import ReportForm
from app.database import Post, Report
from app.api import bp

def get_post_with_details(post_id):
    post = db_manager.get_post_by_id(post_id)
    if not post:
        return None
    
    user_id = session.get('id') # Obter o ID do usuário logado

    # Carregar contagens de likes/dislikes do post e reação do usuário
    post_likes = db_manager.count_reactions_for_post(post_id, 'like_post')
    post_dislikes = db_manager.count_reactions_for_post(post_id, 'dislike_post')
    user_post_reaction_type = ""
    if user_id:
        user_post_reaction = db_manager.get_user_post_reaction(user_id, post_id)
        if user_post_reaction:
            user_post_reaction_type = user_post_reaction.type

    # Carregar comentários e suas respostas com contagens e reações do usuário
    comments_with_details = get_post_comments(post_id, offset=0, limit=10)
    comment_count = db_manager.get_comment_amount_for_post(post_id)

    return {
        'post': post,
        'comments_with_details': comments_with_details,
        'post_likes': post_likes,
        'post_dislikes': post_dislikes,
        'user_post_reaction': user_post_reaction_type,
        'comment_count': comment_count,
        'next_offset': len(comments_with_details),
        'total_comments': comment_count
    }


def get_post_comments(post_id, offset=0, limit=10):
    comentarios = db_manager.get_paginated_comments(post_id, offset, limit)
    formatted_comments = []

    for comment, likes, dislikes, num_replies in comentarios:
        comment_content = {
            'comment': {
                'id': comment.id,
                'username': comment.user_who_interacted.username,
                'userid': comment.user_who_interacted.id,
                'value': comment.value
            },
            'likes': likes,
            'dislikes': dislikes,
            'total_replies': num_replies,
        }

        reaction = db_manager.get_user_comment_reaction(session.get('id'), comment.id)
        if reaction:
            comment_content['user_reaction'] = reaction.type
        
        if num_replies > 0:
            most_liked_reply = db_manager.get_paginated_replies(post_id, comment.id, offset=0, limit=1)
            if most_liked_reply:
                for reply, likes, dislikes in most_liked_reply:
                    comment_content['most_liked_reply'] = {
                        'reply': {
                            'id': reply.id,
                            'username': reply.user_who_interacted.username,
                            'userid': reply.user_who_interacted.id,
                            'value': reply.value
                        },
                        'likes': likes,
                        'dislikes': dislikes
                    }
                
                reply_reaction = db_manager.get_user_comment_reaction(session.get('id'), comment_content['most_liked_reply']["reply"]['id'])
                if reply_reaction:
                    comment_content['reply_user_reaction'] = reply_reaction.type
        
        formatted_comments.append(comment_content)
    
    return formatted_comments

def get_comment_replies(post_id, comment_id, offset=0, limit=10):
    replies = db_manager.get_paginated_replies(post_id, comment_id, offset, limit)
    formatted_replies = []

    for reply, likes, dislikes in replies:
        reply_content = {
            'reply': {
                'id': reply.id,
                'username': reply.user_who_interacted.username,
                'userid': reply.user_who_interacted.id,
                'value': reply.value
            },
            'likes': likes,
            'dislikes': dislikes
        }

        reaction = db_manager.get_user_comment_reaction(session.get('id'), reply.id)
        if reaction:
            reply_content['user_reaction'] = reaction.type
        
        formatted_replies.append(reply_content)
    
    return formatted_replies

@bp.route('/posts/<int:post_id>/react', methods=['POST'])
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

@bp.route('/comments/<int:comment_id>/react', methods=['POST'])
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

@bp.route('/posts/<int:post_id>/comment', methods=['POST'])
@login_required
def comment_post_api(post_id):
    user_id = session.get('id')
    comment_text = request.json.get('comment_text')

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
            "comment_content": {
                "comment": {
                    "id": new_comment.id,
                    "username": new_comment.user_who_interacted.username,
                    "userid": new_comment.user_who_interacted.id,
                    "value": new_comment.value
                },
                "likes": 0,
                "dislikes": 0,
                "user_reaction": None,  # Inicialmente sem reação do usuário
                "replies": []
            }
        }), 200
    else:
        return jsonify({"success": False, "message": result}), 500

@bp.route('/comments/<int:parent_comment_id>/reply', methods=['POST'])
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
            "reply_content": {
                "reply": {
                    "id": new_reply.id,
                    "username": new_reply.user_who_interacted.username,
                    "userid": new_reply.user_who_interacted.id,
                    "value": new_reply.value
                },
                "likes": 0,
                "dislikes": 0,
                "user_reaction": None
            }
        }), 200
    else:
        return jsonify({"success": False, "message": result}), 500

# Rota para pegar detalhes de um post
@bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post_details_api(post_id):
    post_details = get_post_with_details(post_id)
    if not post_details:
        return jsonify({"success": False, "message": "Post não encontrado."}), 404
    
    return jsonify({
        "success": True,
        "post": {
            "id": post_details['post'].id,
            "title": post_details['post'].title,
            "content": post_details['post'].content,
            "tag": post_details['post'].tag,
            "optional_tags": post_details['post'].optional_tags,
            "image_urls": post_details['post'].image_urls,
            "created_at": post_details['post'].created_at.strftime('%d/%m/%Y'),
            "username": post_details['post'].author_user.username,
            "userid": post_details['post'].author_user.id,
        },
        "comments": post_details['comments_with_details'],
        "likes": post_details['post_likes'],
        "dislikes": post_details['post_dislikes'],
        "user_post_reaction": post_details['user_post_reaction'],
        "next_offset": post_details['next_offset'],
        "total_comments": post_details['total_comments']
    }), 200

# Rota para buscar comentários
@bp.route('/posts/<int:post_id>/comments', methods=['GET'])
@login_required
def get_post_comments_api(post_id):
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 10, type=int)

    comments = get_post_comments(post_id, offset, limit)

    return jsonify({"success": True, "comments": comments}), 200

@bp.route('/posts/<int:post_id>/comment/<int:comment_id>/replies', methods=['GET'])
@login_required
def get_comment_replies_api(post_id, comment_id):
    replies_data = get_comment_replies(post_id, comment_id, offset=0, limit=0)

    return jsonify({"success": True, "replies": replies_data}), 200

@bp.route('/posts/<int:post_id>/counts', methods=['GET'])
@login_required
def get_post_interactions_api(post_id):
    likes_count = db_manager.count_reactions_for_post(post_id, 'like_post')
    dislikes_count = db_manager.count_reactions_for_post(post_id, 'dislike_post')
    
    # Obter o estado de reação do usuário logado
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

@bp.route('/comments/<int:comment_id>/counts', methods=['GET'])
@login_required
def get_comment_interactions_api(comment_id):
    likes_count = db_manager.count_reactions_for_comment(comment_id, 'like_comment')
    dislikes_count = db_manager.count_reactions_for_comment(comment_id, 'dislike_comment')

    user_reaction = None
    user_reaction_obj = db_manager.get_user_comment_reaction(user_id, comment_id)
    if user_reaction_obj:
        user_reaction = user_reaction_obj.type # 'like_comment' ou 'dislike_comment'

    return jsonify({
        "success": True, 
        "likes": likes_count, 
        "dislikes": dislikes_count,
        "user_reaction": user_reaction
    }), 200
    
# Exclusão de posts e interações
@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = db_manager.get_post_by_id(post_id)
    if post:
        if post.author_user.id == session.get('id'):
            db_manager.delete_post_by_id(post_id)
            return jsonify({"success": True, "message": "Post excluído com sucesso!"}), 200
        else:
            return jsonify({"success": False, "message": "Você não tem permissão para executar essa ação."}), 403
    return jsonify({"success": False, "message": "Post não encontrado."}), 404

@bp.route('/interaction/<int:interaction_id>/delete', methods=['POST'])
@login_required
def delete_interaction(interaction_id):
    interaction = db_manager.get_interaction_by_id(interaction_id)
    if interaction and interaction.type in ['comment_post', 'reply_comment']:
        if interaction.user_who_interacted.id == session.get('id'):
            with db_manager.get_db() as db:
                db.delete(interaction)
                db.commit()
                return jsonify({"success": True, "message": "Interação excluída com sucesso!"}), 200
        else:
            return jsonify({"success": False, "message": "Você não tem permissão para executar essa ação."}), 403
    return jsonify({"success": False, "message": "Interação não encontrada."}), 404
    
# Denúncias
@bp.route('/report', methods=['POST'])
@login_required
def report():
    form = ReportForm()
    
    if request.is_json:
        json_data = request.get_json()
        if json_data:
            form.category.data = json_data.get('category')
            form.description.data = json_data.get('description')
            form.type.data = json_data.get('type')
            form.target_id.data = json_data.get('target_id')
            form.perpetrator_id.data = json_data.get('id_dono')
        else:
            return jsonify({'success': False, 'message': 'Corpo da requisição JSON inválido ou vazio.'}), 400
    else:
        return jsonify({'success': False, 'message': 'Tipo de conteúdo não suportado. Espera-se JSON.'}), 415 # Unsupported Media Type

    if form.validate():
        user_id = session['id'] # O ID do usuário que está denunciando
        
        with db_manager.get_db() as db:
            try:
                new_report = Report(
                    reporting_user_id=user_id,
                    type=form.type.data,
                    reason=form.category.data,
                    description=form.description.data,
                    reported_item_id=form.target_id.data,
                    perpetrator_id=form.perpetrator_id.data
                )
                db.add(new_report)
                db.commit()
                db.refresh(new_report) # Recarrega o objeto para ter o ID gerado pelo DB
                return jsonify({'success': True, 'message': 'Denúncia enviada com sucesso!', 'id': new_report.id}), 200
            except Exception as e:
                db.rollback()
                return jsonify({'success': False, f'message': 'Erro ao salvar a denúncia. {e}.'}), 500
    else:
        # Erros de validação do formulário
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Dados de denúncia inválidos.'}), 400