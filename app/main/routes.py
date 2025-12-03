from flask import render_template, session, request, jsonify
from app.main import bp
from app.extensions import login_required, db_manager
from app.api.routes import get_user_icon
from app.recommendation import RecommendationEngine, CollaborativeFilteringStrategy, ContentBasedStrategy
import json
import re

# Inicializa o sistema de recomendação e registra as estratégias
recommendation_engine = RecommendationEngine(db_manager)
recommendation_engine.register_strategy(CollaborativeFilteringStrategy(db_manager))
recommendation_engine.register_strategy(ContentBasedStrategy(db_manager))

def get_interactions(post_id):
    likes = db_manager.count_reactions_for_post(post_id, 'like_post')
    dislikes = db_manager.count_reactions_for_post(post_id, 'dislike_post')
    comments = db_manager.count_comments_for_post(post_id)
    user_reaction = db_manager.get_user_post_reaction(session.get('id'), post_id)

    if user_reaction:
        user_reaction = user_reaction.type

    return {
        'likes': likes,
        'dislikes': dislikes,
        'comments': comments,
        'user_reaction': user_reaction
    }

@login_required
def get_recommendations():
    user_id = session.get('id')

    # Obtém os posts recomendados
    post_ids = recommendation_engine.recommend_posts(user_id, top_n=20)
    posts = []
    with db_manager.get_db() as db:
        for post_id in post_ids:
            post = db_manager.get_post_by_id(post_id)
            if post:
                post_reactions = get_interactions(post_id)

                posts.append({
                    'id': post.id,
                    'title': post.title,
                    'content': post.content,
                    'tag': post.tag,
                    'optional_tags': post.optional_tags,
                    'created_at': post.created_at,
                    'author': post.author_user.display_name,
                    'authorat': post.author_user.user.username,
                    'authoricon': post.author_user.icon_url,
                    'userid': post.author_user.user_id,
                    'image_urls': post.image_urls,
                    'likes': post_reactions["likes"],
                    'dislikes': post_reactions["dislikes"],
                    'comments': post_reactions["comments"],
                    'user_reaction': post_reactions["user_reaction"],
                    'is_saved': db_manager.is_post_saved(user_id, post.id) if user_id else False
                })
    return posts

def get_top_rated():
    posts = []
    for post in db_manager.get_posts_with_most_likes():
        post_reactions = get_interactions(post.id)
        posts.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'tag': post.tag,
            'optional_tags': post.optional_tags,
            'created_at': post.created_at,
            'author': post.author_user.display_name,
            'authorat': post.author_user.user.username,
            'authoricon': post.author_user.icon_url,
            'userid': post.author_user.user_id,
            'image_urls': json.loads(post.image_urls) if post.image_urls else [], 
            'likes': post_reactions["likes"],
            'dislikes': post_reactions["dislikes"],
            'comments': post_reactions["comments"],
                    'user_reaction': "",
                    'is_saved': db_manager.is_post_saved(session.get('id'), post.id) if session.get('id') else False
        })
    return posts

@bp.route('/', methods=['GET', 'POST'])
def index():
    if session.get('id'):
        recommendations = get_recommendations()
        return render_template('timeline.html', posts=recommendations, user_name=db_manager.get_user_details(session.get('id')).display_name, user_icon=get_user_icon(session.get('id')))
    else:
        top_rated = get_top_rated()
        return render_template('timeline.html', posts=top_rated)

@bp.route('/pesquisar', methods=['GET', 'POST'])
def search():
    """Página de resultados de pesquisa."""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return render_template('search_results.html', query='', category_filter=None, total_results=0, posts=[], search_error='Por favor, forneça uma consulta de pesquisa válida.')
    
    # Extrai filtro de categoria entre parênteses
    category_filter = None
    category_match = re.search(r'\(([^)]+)\)', query)
    if category_match:
        category_filter = category_match.group(1).strip()
        query = query.replace(f'({category_match.group(1)})', '').strip()
    
    with db_manager.get_db() as db:
        from app.database import Post
        
        # Query base: busca por título, conteúdo, tag ou optional_tags
        posts_query = db.query(Post).filter(
            Post.is_deleted == False
        ).filter(
            (Post.title.ilike(f'%{query}%')) |
            (Post.content.ilike(f'%{query}%')) |
            (Post.tag.ilike(f'%{query}%')) |
            (Post.optional_tags.ilike(f'%{query}%'))
        )
        
        # Aplica filtro de categoria se fornecido
        if category_filter:
            posts_query = posts_query.filter(
                (Post.tag.ilike(f'%{category_filter}%')) |
                (Post.optional_tags.ilike(f'%{category_filter}%'))
            )
        
        from sqlalchemy.orm import joinedload
        from app.database import UserDetails
        
        posts_db = posts_query.options(
            joinedload(Post.author_user).joinedload(UserDetails.user)
        ).order_by(Post.created_at.desc()).all()
        
        posts = []
        user_id = session.get('id')
        
        for post in posts_db:
            post_reactions = {
                'likes': db_manager.count_reactions_for_post(post.id, 'like_post'),
                'dislikes': db_manager.count_reactions_for_post(post.id, 'dislike_post'),
                'comments': db_manager.count_comments_for_post(post.id),
                'user_reaction': ""
            }
            
            if user_id:
                user_reaction = db_manager.get_user_post_reaction(user_id, post.id)
                if user_reaction:
                    post_reactions['user_reaction'] = user_reaction.type
            
            image_urls = []
            if post.image_urls:
                image_urls = json.loads(post.image_urls)
            
            posts.append({
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'tag': post.tag,
                'optional_tags': post.optional_tags,
                'created_at': post.created_at,
                'author': post.author_user.display_name,
                'authorat': post.author_user.user.username,
                'authoricon': post.author_user.icon_url,
                'userid': post.author_user.user_id,
                'image_urls': image_urls,
                'likes': post_reactions["likes"],
                'dislikes': post_reactions["dislikes"],
                'comments': post_reactions["comments"],
                'user_reaction': post_reactions["user_reaction"],
                'is_saved': db_manager.is_post_saved(user_id, post.id) if user_id else False
            })
    
    user_name = None
    if session.get('id'):
        user_details = db_manager.get_user_details(session.get('id'))
        if user_details:
            user_name = user_details.display_name
    
    return render_template('search_results.html', 
                         query=query, 
                         category_filter=category_filter, 
                         total_results=len(posts), 
                         posts=posts,
                         user_name=user_name,
                         user_icon=get_user_icon(session.get('id')))


@bp.route('/salvos', methods=['GET'])
@login_required
def saved_posts():
    user_id = session.get('id')
    posts = []
    with db_manager.get_db() as db:
        from app.database import Post
        saved = db_manager.get_saved_posts(user_id)
        for post in saved:
            posts.append({
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'tag': post.tag,
                'optional_tags': post.optional_tags,
                'created_at': post.created_at,
                'author': post.author_user.display_name,
                'authorat': post.author_user.user.username,
                'authoricon': post.author_user.icon_url,
                'userid': post.author_user.user_id,
                'image_urls': post.image_urls,
            })

    return render_template('saved_posts.html', posts=posts, user_icon=get_user_icon(user_id), user_name=db_manager.get_user_details(user_id).display_name)