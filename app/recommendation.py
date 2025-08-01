from app.database import DatabaseManager, User, Post, Interaction
from collections import defaultdict

class RecommendationStrategy:
    def get_scores(self, user_id):
        raise NotImplementedError

class CollaborativeFilteringStrategy(RecommendationStrategy):
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_scores(self, user_id):
        with self.db_manager.get_db() as db:
            # Busca posts que o usuário curtiu
            liked_posts = db.query(Interaction.post_id).filter(
                Interaction.user_id == user_id,
                Interaction.type == 'like_post'
            ).all()
            liked_post_ids = [p.post_id for p in liked_posts]

            # Busca outros usuários que curtiram os mesmos posts
            similar_users = db.query(Interaction.user_id).filter(
                Interaction.post_id.in_(liked_post_ids),
                Interaction.type == 'like_post',
                Interaction.user_id != user_id
            ).distinct().all()

            # Busca posts que esses usuários curtiram e que o usuário atual não curtiu
            similar_user_ids = [u.user_id for u in similar_users]
            recommended_posts = db.query(Interaction.post_id).filter(
                Interaction.user_id.in_(similar_user_ids),
                Interaction.type == 'like_post',
                ~Interaction.post_id.in_(liked_post_ids)
            ).all()

            scores = defaultdict(int) # Dicionário para armazenar pontuação dos posts
            for p in recommended_posts:
                scores[p.post_id] += 1 # Soma 1 para cada vez que o post é recomendado

            # Inclui posts sem nenhuma interação e que o usuário ainda não curtiu
            all_post_ids = set([pid for (pid,) in db.query(Post.id).all()])
            already_seen = set(liked_post_ids) | set(scores.keys())
            # Busca posts que o usuário não curtiu e que não estão nas recomendações
            for post_id in all_post_ids:
                if post_id not in already_seen:
                    scores[post_id] += 0.5  # Score menor para posts "frios"
            return scores # Retorna {post_id: score}

class ContentBasedStrategy(RecommendationStrategy):
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_scores(self, user_id):
        with self.db_manager.get_db() as db:
            # Busca categorias/tags dos posts que o usuário interagiu
            user_interactions = db.query(Post.tag, Post.optional_tags).join(
                Interaction, Interaction.post_id == Post.id
            ).filter(
                Interaction.user_id == user_id
            ).all()
            tags = set() # Conjunto para armazenar tags/categorias
            for tag, optional_tags in user_interactions:
                tags.add(tag)
                if optional_tags:
                    tags.update(optional_tags.split(',')) # Separa e adiciona sub-tags
            
            # Busca todos os posts e compara as tags
            posts = db.query(Post.id, Post.tag, Post.optional_tags).all()
            scores = defaultdict(int) # Dicionário para pontuação
            for post_id, tag, optional_tags in posts:
                score = 0
                if tag in tags:
                    score += 2 # Pontuação maior para categoria principal
                if optional_tags:
                    for t in optional_tags.split(','):
                        if t in tags:
                            score += 1 # Pontuação para sub-tags
                if score > 0:
                    scores[post_id] = score # Só adiciona se houver pontuação
            return scores # Retorna {post_id: score}

class RecommendationEngine:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.strategies = [] # Lista de estratégias registradas

    def register_strategy(self, strategy):
        self.strategies.append(strategy) # Adiciona uma estratégia

    def recommend_posts(self, user_id, top_n=10):
        combined_scores = defaultdict(float) # Dicionário para somar pontuações de todas estratégias
        for strategy in self.strategies:
            scores = strategy.get_scores(user_id) # Obtém pontuações da estratégia
            for post_id, score in scores.items():
                combined_scores[post_id] += score # Soma pontuações
        recommended = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True) # Ordena por score
        return [post_id for post_id, score in recommended[:top_n]] # Retorna os IDs dos posts recomendados
