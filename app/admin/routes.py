from flask import render_template, session, request, jsonify
from app.extensions import power_required, db_manager
from app.database import Report, User, Post, Interaction, ModerationHistory
from app.data_sanitizer import ModerationForm
from sqlalchemy import func
from datetime import date, datetime
from app.admin import bp

# Aplicando ações de moderação
def thealmightyhammer(action: ModerationHistory):
    if action.target_type == 'post' and action.action_type == 'deletar':
        db_manager.delete_post_by_id(action.target_id)
    elif action.target_type == 'interaction' and action.action_type == 'deletar':
        db_manager.delete_interaction_by_id(action.target_id)
    elif action.target_type == 'user':
        # Lógica para silenciar, advertir, banir, etc.
        pass

def resolve_report(report_id: int, moderator_id: int):
    with db_manager.get_db() as db:
        report = db.query(Report).filter(Report.id == report_id, Report.status == 'pendente').first()
        if report:
            report.status = 'resolvido'
            report.moderator_id = moderator_id
            report.resolved_at = datetime.now()
            db.commit()
            return True
        return False

# Rotas
@bp.route('/', methods=['GET'])
@power_required(required_power=1)
def index():
    return render_template('admin.html', username=session.get('username'), power=session.get('power'))

@bp.route('/reports', methods=['GET'])
@power_required(required_power=1)
def reports():
    with db_manager.get_db() as db:
        reports = db.query(Report).order_by(Report.creation_date.desc()).all()
        return jsonify({"sucess": True, "reports": [
            {
                'id': report.id,
                'category': report.reason,
                'type': report.type,
                'reported_item_id': report.reported_item_id,
                'description': report.description,
                'reporting_user_id': report.reporting_user_id,
                'perpetrator_id': report.perpetrator_id,
                'status': report.status,
                'moderator_id': report.moderator_id,
                'resolved_at': report.resolved_at,
                'creation_date': report.creation_date.strftime('%d/%m/%Y %H:%M')
            } for report in reports
        ]}), 200

@bp.route('/reports/<int:report_id>/resolve', methods=['POST'])
@power_required(required_power=1)
def resolve_report_request(report_id):
    moderator_id = session.get('id')

    if resolve_report(report_id, moderator_id):
        return jsonify({'success': True, 'message': 'Denúncia resolvida com sucesso.'}), 200
    else:
        return jsonify({'success': False, 'message': 'Denúncia não encontrada ou já resolvida.'}), 404

@bp.route('/hunt', methods=['GET'])
@power_required(required_power=1)
def hunt():
    user_id = request.args.get('user_id', type=int)
    include_posts = request.args.get('include_posts', 'false') == 'true'
    include_interactions = request.args.get('include_interactions', 'false') == 'true'
    include_reports = request.args.get('include_reports', 'false') == 'true'
    result = {}
    
    with db_manager.get_db() as db:
        moderation_history = db.query(ModerationHistory).filter(ModerationHistory.user_id == user_id).order_by(ModerationHistory.created_at.desc()).all()
        result['moderation_history'] = [
            {
                'action_type': historico.action_type,
                'reason': historico.reason,
                'is_active': historico.is_active,
                'target_type': historico.target_type,
                'target_id': historico.target_id,
                'end_date': historico.end_date.strftime('%d/%m/%Y') if historico.end_date else None,
                'moderator_id': historico.moderator_id,
                'created_at': historico.created_at.strftime('%d/%m/%Y %H:%M')
            } for historico in moderation_history
        ]
    
    if include_posts:
        posts = db_manager.get_user_posts(user_id)
        result['posts'] = [{
            'id': post.id,
            'titulo': post.title,
            'is_deleted': post.is_deleted,
            'creation_date': post.created_at.strftime('%d/%m/%Y %H:%M')
        } for post in posts]
    if include_interactions:
        comments_n_replies = db_manager.get_user_comments_n_replies(user_id)
        result['interactions'] = [
                {
                    'id': interaction.id,
                    'post_id': interaction.post_id,
                    'type': interaction.type,
                    'value': interaction.value,
                    'creation_date': interaction.timestamp.strftime('%d/%m/%Y %H:%M')
                } for interaction in comments_n_replies
            ]
    if include_reports:
        with db_manager.get_db() as db:
            reports = db.query(Report).filter(Report.perpetrator_id == user_id).all()
            result['reports'] = [
                {
                    'id': report.id,
                    'category': report.reason,
                    'type': report.type,
                    'reported_item_id': report.reported_item_id,
                    'perpetrator_id': report.perpetrator_id,
                    'description': report.description,
                    'status': report.status,
                    'moderator_id': report.moderator_id,
                    'resolved_at': report.resolved_at,
                    'creation_date': report.creation_date.strftime('%d/%m/%Y %H:%M')
                } for report in reports
            ]
    return jsonify(result)

@bp.route('/feeltheweightofthehammer', methods=['POST'])
@power_required(required_power=1)
def feeltheweightofthehammer():
    json_data = request.get_json()
    if not json_data:
        return jsonify({'success': False, 'message': 'Corpo da requisição JSON inválido ou vazio.'}), 400

    form = ModerationForm(data=json_data)

    if form.validate():
        end_date = form.end_date.data

        is_active = True
        if end_date and end_date < date.today():
            is_active = False
        
        user_id_to_penalize = None
        target_type = form.type.data
        target_id = form.target_id.data

        # Encontra o ID do usuário ofensor para registrar no histórico
        if target_type == 'user':
            user_id_to_penalize = target_id
        elif target_type == 'post':
            post = db_manager.get_post_by_id(target_id)
            if post:
                user_id_to_penalize = post.user_id
        elif target_type == 'interaction':
            interaction = db_manager.get_interaction_by_id(target_id)
            if interaction:
                user_id_to_penalize = interaction.user_id

        with db_manager.get_db() as db:
            try:
                action = ModerationHistory(
                    target_type=target_type,
                    action_type=form.mod_action.data,
                    target_id=target_id,
                    user_id=user_id_to_penalize, # Garante que o usuário penalizado seja registrado
                    reason=form.reason.data,
                    is_active=is_active,
                    end_date=end_date,
                    moderator_id=session['id']
                )
                db.add(action)
                db.commit()
                db.refresh(action)

                # Executa a ação após registrar
                thealmightyhammer(action)
                return jsonify({'success': True, 'message': 'Ação de moderação aplicada com sucesso.'}), 201
            except Exception as e:
                db.rollback()
                return jsonify({'success': False, 'message': f'Erro ao salvar no banco de dados: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': form.errors}), 400

@bp.route('/changepower', methods=['POST'])
@power_required(required_power=2)
def powersurge():
    json_data = request.get_json()
    if not json_data:
        return jsonify({'success': False, 'message': 'Corpo da requisição JSON inválido ou vazio.'}), 400
    
    user_id = json_data['user_id']
    power = int(json_data['power'])

    if power > 3:
        return jsonify({'success': False, 'message': f'O poder não pode exceder 3'}), 500
    elif power < 0:
        return jsonify({'success': False, 'message': f'O poder não pode ser negativo'}), 500

    with db_manager.get_db() as db:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if user.power >= session.get('power'):
                    return jsonify({'success': False, 'message': f'Você não pode alterar o poder de um superior'}), 500
                else:
                    user.power = power
                    db.commit()
            else:
                return jsonify({'success': False, 'message': f'O usuário não existe'}), 500
        except Exception as e:
            db.rollback()
            return jsonify({'success': False, 'message': f'Erro ao alterar o poder do usuário: {str(e)}'}), 500
        return jsonify({'success': True, 'message': f'Poder alterado para {power} com sucesso'}), 200

@bp.route('/analytics', methods=['GET'])
@power_required(required_power=1)
def analytics():
    with db_manager.get_db() as db:
        users = db.query(func.count(User.id)).scalar()
        posts = db.query(func.count(Post.id)).scalar()
        interactions = db.query(func.count(Interaction.id)).filter(Interaction.type.in_(['post_comment', 'reply_comment'])).scalar()
        reactions = db.query(func.count(Interaction.id)).filter(Interaction.type.in_(['like_post', 'dislike_post'])).scalar()
        chart = {
            'type': 'bar',
            'data': {
                'labels': ['Total usuários', 'Total posts', 'Total comentários', 'Total reações em posts'],
                'datasets': [{
                    'label': 'Total',
                    'data': [users, posts, interactions, reactions],
                    'backgroundColor': [
                        'rgba(59,255,130,0.7)',
                        'rgba(59,255,246,0.7)',
                        'rgba(255,130,22,0.7)',
                        'rgba(255,0,22,0.7)'
                    ]
                }]
            }
        }
        return jsonify({'chart': chart, 'text': f'Tudo: {users + posts + interactions + reactions}'})
