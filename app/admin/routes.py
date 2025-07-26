from flask import render_template, session, request, jsonify
from app.extensions import power_required, db_manager
from app.database import Report
from app.admin import bp
from collections import Counter

@bp.route('/', methods=['GET'])
@power_required(required_power=1)
def index():
    return render_template('admin.html', username=session.get('username'))

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

@bp.route('/hunt', methods=['GET'])
@power_required(required_power=1)
def hunt():
    user_id = request.args.get('user_id', type=int)
    include_posts = request.args.get('include_posts', 'false') == 'true'
    include_interactions = request.args.get('include_interactions', 'false') == 'true'
    include_interactions = request.args.get('include_reports', 'false') == 'true'
    result = {}
    
    moderation_history = db_manager.get_moderation_history(user_id)
    result['moderation_history'] = [
        {
            'action_type': historico.action_type,
            'reason': historico.reason,
            'is_active': historico.is_active,
            'start_date': historico.start_date.strftime('%d/%m/%Y'),
            'end_date': historico.end_date.strftime('%d/%m/%Y'),
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
    if include_interactions:
        with db_manager.get_db() as db:
            reports = db.query(Report).filter(Report.reported_id == user_id, Report.type == "usuario").all()
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
    data = request.json
    mod_type = data.get('type')
    target_id = data.get('target_id')
    reason = data.get('reason')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    mod_action = data.get('mod_action')
    moderator_id = session.get('id')
    is_active = True
    
    try:
        if mod_type == 'user':
            db_manager.add_moderation_action(
                action_type=mod_action,
                reason=reason,
                is_active=is_active,
                start_date=start_date,
                end_date=end_date,
                moderator_id=moderator_id,
                user_id=target_id
            )
        else:
            db_manager.add_moderation_action(
                action_type=mod_action,
                reason=reason,
                is_active=is_active,
                start_date=start_date,
                end_date=end_date,
                moderator_id=moderator_id,
                post_id=target_id
            )
        return jsonify({'message': 'Ação de moderação registrada com sucesso.'}), 200
    except Exception as e:
        return jsonify({'message': f'Erro: {str(e)}'}), 400

@bp.route('/analytics', methods=['GET'])
@power_required(required_power=1)
def analytics():
    reports = db_manager.get_reports()
    types = [report['type'] for report in reports]
    counter = Counter(types)
    chart = {
        'type': 'bar',
        'data': {
            'labels': list(counter.keys()),
            'datasets': [{
                'label': 'Denúncias por tipo',
                'data': list(counter.values()),
                'backgroundColor': 'rgba(59,130,246,0.7)'
            }]
        }
    }
    return jsonify({'chart': chart, 'text': f'Total de denúncias: {len(reports)}'})