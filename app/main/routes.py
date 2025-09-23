from flask import render_template, session
from app.main import bp
from app.extensions import login_required, db_manager
from app.api.routes import get_user_icon
from app.recommendation import RecommendationEngine, CollaborativeFilteringStrategy, ContentBasedStrategy
import json

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
                    'user_reaction': post_reactions["user_reaction"]
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
            'user_reaction': ""
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