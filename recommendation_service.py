import numpy as np
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity

class RecommendationService:
    def __init__(self, db_manager):
        self.db = db_manager
        # Pesos para cada tipo de interação. Ajuste conforme necessário.
        self.interaction_weights = {
            'view': 1,
            'like': 3,
            'comment': 4,
            # Você pode adicionar 'downvote': -2 se implementar
        }

    def _get_interaction_data(self):
        """Busca todas as interações e as transforma em uma matriz usuário-item."""
        interactions = self.db.get_all_interactions()
        if not interactions:
            return None, None, None

        # Mapeia emails e post_ids para índices numéricos para a matriz
        all_users = sorted(list(set(row[0] for row in interactions)))
        all_posts = sorted(list(set(row[1] for row in interactions)))
        
        user_map = {email: i for i, email in enumerate(all_users)}
        post_map = {post_id: i for i, post_id in enumerate(all_posts)}

        # Cria a matriz de interações com zeros
        matrix = np.zeros((len(user_map), len(post_map)))

        # Preenche a matriz com os pesos das interações
        for email, post_id, interaction_type in interactions:
            if email in user_map and post_id in post_map:
                user_idx = user_map[email]
                post_idx = post_map[post_id]
                matrix[user_idx, post_idx] += self.interaction_weights.get(interaction_type, 0)
            
        return matrix, user_map, post_map

    def _calculate_item_similarity(self, matrix):
        """Calcula a similaridade do cosseno entre todos os pares de itens (posts)."""
        # Transpomos a matriz para que os itens (posts) fiquem nas linhas
        # e calculamos a similaridade entre eles.
        item_similarity_matrix = cosine_similarity(matrix.T)
        return item_similarity_matrix

    def get_recommendations(self, user_email, n=10):
        """
        Gera uma lista de N posts recomendados para um determinado usuário.
        """
        interaction_matrix, user_map, post_map = self._get_interaction_data()

        # Se não houver dados ou o usuário for novo, não há recomendações
        if interaction_matrix is None or user_email not in user_map:
            return []

        item_similarity = self._calculate_item_similarity(interaction_matrix)
        
        user_idx = user_map[user_email]
        user_interactions = interaction_matrix[user_idx, :]

        # Calcula a pontuação de recomendação para todos os posts
        # score(p) = Σ (similaridade(p, i) * pontuação_usuario(i)) para todos os posts i
        recommendation_scores = item_similarity.dot(user_interactions)

        # Remove os posts com os quais o usuário já interagiu
        interacted_posts_indices = np.where(user_interactions > 0)[0]
        recommendation_scores[interacted_posts_indices] = -1 # Marcar para ignorar

        # Obtém os índices dos N posts com maior pontuação
        # np.argsort retorna os índices que ordenariam o array
        recommended_post_indices = np.argsort(recommendation_scores)[::-1][:n]

        # Mapeia os índices de volta para os post_ids originais
        post_map_inv = {i: post_id for post_id, i in post_map.items()}
        
        recommended_post_ids = [
            post_map_inv[i] for i in recommended_post_indices 
            if i in post_map_inv and recommendation_scores[i] > 0
        ]

        return recommended_post_ids
