import os
from datetime import datetime, timedelta
from argon2 import PasswordHasher, exceptions
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, SmallInteger, desc, func, case
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
import contextlib
import json

from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    power = Column(SmallInteger, default=0)
    creation_date = Column(DateTime, default=datetime.now)
    active = Column(Boolean, default=False)

    # Relacionamentos
    user_details = relationship("UserDetails", foreign_keys="[UserDetails.user_id]", back_populates="user")
    
    # Modereção
    moderations_received = relationship("ModerationHistory", foreign_keys="[ModerationHistory.user_id]", back_populates="offending_user")
    moderations_made = relationship("ModerationHistory",foreign_keys="[ModerationHistory.moderator_id]", back_populates="moderator")
    
    reports_handled = relationship("Report", foreign_keys="[Report.moderator_id]", back_populates="moderator")
    reports_made = relationship("Report", foreign_keys="[Report.reporting_user_id]", back_populates="reporting_user")
    reports_against = relationship("Report", foreign_keys="[Report.perpetrator_id]", back_populates="reported_user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class UserDetails(Base):
    __tablename__ = 'users_details'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    display_name = Column(String(32), nullable=True, default=None)
    bio = Column(Text, nullable=True, default=None)
    badges = Column(Text, nullable=True, default="{}")
    icon_url = Column(Text, nullable=True, default=None)
    banner_url = Column(Text, nullable=True, default=None)

    # Relacionamentos
    user = relationship("User", foreign_keys=[user_id], back_populates="user_details")
    posts = relationship("Post", foreign_keys="[Post.user_id]", back_populates="author_user")
    interactions = relationship("Interaction", foreign_keys="[Interaction.user_id]", back_populates="user_who_interacted")

    def __repr__(self):
        return f"<UserDetails(id={self.id}, display_name='{self.display_name}', user_id='{self.user_id}')>"

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users_details.user_id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tag = Column(String(25))
    optional_tags = Column(String(75))
    created_at = Column(DateTime, default=datetime.now)
    image_urls = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)

    # Relacionamentos
    author_user = relationship("UserDetails", foreign_keys=[user_id], back_populates="posts")
    interactions = relationship("Interaction", foreign_keys="[Interaction.post_id]", back_populates="post_being_interacted")
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', user_id='{self.user_id}')>"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users_details.user_id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    parent_interaction_id = Column(Integer, ForeignKey('interactions.id'), nullable=True) 
    type = Column(String(50), nullable=False)  # 'like_post', 'dislike_post', 'comment_post', 'like_comment', 'dislike_comment', 'reply_comment', 'view_post', 'share_post'
    value = Column(String(352), nullable=True) # "@(usuário) " + 300 caracteres de comentários
    is_deleted = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now)

    # Relacionamentos
    user_who_interacted = relationship("UserDetails", back_populates="interactions", foreign_keys=[user_id])
    post_being_interacted = relationship("Post", back_populates="interactions", foreign_keys=[post_id])
    
    # Hierarquia de comentários
    parent_interaction = relationship("Interaction", remote_side=[id], back_populates="child_interactions")
    child_interactions = relationship("Interaction", back_populates="parent_interaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Interaction(id='{self.id}', post_id='{self.post_id}', user_id='{self.user_id}', type='{self.type}', parent_id={self.parent_interaction_id})>"

class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True, index=True)
    reporting_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(50), nullable=False) # 'usuario', 'post', 'interacao'
    reason = Column(String(50), nullable=True)
    description = Column(String(300), nullable=True)
    reported_item_id = Column(Integer, nullable=False)
    perpetrator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    status = Column(String(50), default='pendente', nullable=False) # pendente, em_revisao, resolvido, rejeitado, arquivado
    moderator_id = Column(Integer, ForeignKey('users.id'), nullable=True) # O moderador que lidou com o relatório
    resolved_at = Column(DateTime, nullable=True)
    creation_date = Column(DateTime, default=datetime.now)

    #Relacionamentos
    reporting_user = relationship("User", foreign_keys=[reporting_user_id], back_populates="reports_made")
    reported_user = relationship("User", foreign_keys=[perpetrator_id], back_populates="reports_against")
    moderator = relationship("User", foreign_keys=[moderator_id], back_populates="reports_handled")
    
    def __repr__(self):
        return f"<Report(id={self.id}, type='{self.type}', status='{self.status}', reporting_user_id={self.reporting_user_id})>"

class ModerationHistory(Base):
    __tablename__ = 'moderation_history'
    id = Column(Integer, primary_key=True, index=True)
    action_type = Column(String(50), nullable=False) # mute, shadow-ban, ban, deactivation
    reason = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    end_date = Column(DateTime, nullable=True)
    moderator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey('users.id'))
    target_id = Column(Integer, nullable=False)
    target_type = Column(String(50), nullable=False)
    
    # Relacionamentos
    moderator = relationship("User", foreign_keys=[moderator_id], back_populates="moderations_made")
    offending_user = relationship("User", foreign_keys=[user_id], back_populates="moderations_received")

class DatabaseManager:
    def __init__(self):
        # A conexão e sessão são gerenciadas pelo SessionLocal
        self.ph = PasswordHasher() # Instancia o PasswordHasher uma vez

    @contextlib.contextmanager
    def get_db(self):
        """Retorna uma nova sessão de banco de dados."""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Helper para obter usuário de forma consistente
    def _get_user_by_field(self, field_name: str, value):
        with self.get_db() as db:
            if field_name == 'email':
                return db.query(User).filter(User.email == value).first()
            elif field_name == 'username':
                return db.query(User).filter(User.username == value).first()
            elif field_name == 'id':
                return db.query(User).filter(User.id == value).first()
            return None

    # Helper para registrar interações
    def _register_interaction(self, user_id: int, post_id: int, interaction_type: str, value: str = None, parent_interaction_id: int = None):
        with self.get_db() as db:
            try:
                new_interaction = Interaction(
                    user_id=user_id,
                    post_id=post_id,
                    type=interaction_type,
                    value=value,
                    parent_interaction_id=parent_interaction_id
                )
                db.add(new_interaction)
                db.commit()
                db.refresh(new_interaction) # Recarrega o objeto para ter o ID gerado pelo DB
                return True, new_interaction.id
            except Exception as e:
                db.rollback()
                return False, f"Erro inesperado ao salvar interação: {e}"

    def init_all_dbs(self):
        """Cria todas as tabelas definidas nos modelos no banco de dados."""
        try:
            Base.metadata.create_all(bind=engine)
            print("Tabelas criadas ou já existentes no PostgreSQL.")
        except OperationalError as e:
            print(f"Erro ao conectar ou criar tabelas: {e}")
            print("Verifique a DATABASE_URL e as credenciais do PostgreSQL.")
        except Exception as e:
            print(f"Um erro inesperado ocorreu durante a inicialização do DB: {e}")
    
    def get_user(self, _type: str, value):
        """Retorna um usuário pelo tipo (email, username, id) e valor."""
        with self.get_db() as db:
            user = self._get_user_by_field(_type, value)
            return user if user else False

    def get_user_details(self, user_id: int):
        """Retorna os detalhes do perfil de um usuário a partir do ID"""
        with self.get_db() as db:
            user = db.query(UserDetails).options(joinedload(UserDetails.user)).filter(UserDetails.user_id == user_id).first()
            return user if user else False

    def check_user_activation(self, _type, identification):
        """
        Verifica a ativação do usuário e lida com contas não ativas expiradas.
        Retorna (True, True) para sucesso, (False, mensagem) para erro/problema.
        """
        with self.get_db() as db:
            user_data = self._get_user_by_field(_type, identification)

            if user_data:
                if not user_data.active: # active é False (0)
                    diferencaTempo = datetime.now() - user_data.creation_date
                    if diferencaTempo > timedelta(hours=1):
                        # Deletar conta expirada
                        db.query(User).filter(User.email == user_data.email).delete()
                        db.commit()
                        return True, True # Conta deletada, pode prosseguir com novo registro
                    else:
                        minutes_left = 60 - int(diferencaTempo.total_seconds() / 60)
                        return False, f"Já existe uma conta com \"{identification}\" em processo de ativação. Faltam {minutes_left} minutos"
                else:
                    return False, f"Conta com \"{identification}\" já registrada."
            return True, True # Usuário não encontrado, pode prosseguir

    def save_user(self, username, email, password, power = 0, active=False):
        """Salva um novo usuário no banco de dados.
        Assume que as validações de existência e ativação já foram feitas externamente
        pelo chamador (ex: na rota de registro).
        """
        with self.get_db() as db:
            try:
                hashed_password = self.ph.hash(password)
                new_user = User(
                    username=username,
                    email=email,
                    password=hashed_password,
                    power=power,
                    active=active
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user) # Recarrega o objeto para ter o ID gerado pelo DB
                return True, None
            except IntegrityError as e:
                db.rollback()
                if "users_email_key" in str(e):
                    return False, "O email já está registrado."
                elif "users_username_key" in str(e):
                    return False, "O nome de usuário já está em uso."
                
                return False, f"Erro ao salvar usuário: {e}"
            except Exception as e:
                db.rollback()
                return False, f"Erro inesperado ao salvar usuário: {e}"

    def delete_user(self, email):
        """Deleta um usuário pelo email."""
        with self.get_db() as db:
            result = db.query(User).filter(User.email == email).delete(synchronize_session=False)
            db.commit()
            return result # Retorna o número de linhas afetadas (0 ou 1)

    def activate_user(self, email):
        """Ativa a conta de um usuário."""
        with self.get_db() as db:
            user = db.query(User).filter(User.email == value).first()
            if user:
                user.active = True
                db.commit()
                db.refresh()
            return user.id if user else False # Retorna o ID se o usuário foi encontrado e atualizado

    def create_user_profile(self, user_id):
        """Cria o perfil do usuário."""
        with self.get_db() as db:
            try:
                new_profile = UserDetails(user_id=user_id)
                db.add(new_profile)
                db.commit()
                return True
            except IntegrityError as e:
                db.rollback()
                print(f"Erro ao criar perfil de usuário: {e}")
                return False
            except Exception as e:
                db.rollback()
                print(f"Erro inesperado ao criar perfil de usuário: {e}")
                return False

    def logto_user(self, login, password, _type):
        """Verifica as credenciais do usuário para login."""
        with self.get_db() as db:
            user = self._get_user_by_field(_type, login)
            if user and user.active: # Apenas usuários ativos podem logar
                try:
                    self.ph.verify(user.password, password)

                    active_penalties = self.check_and_update_user_penalties(user.id)
                    
                    is_banned = any(p.action_type == 'banir' for p in active_penalties)
                    if is_banned:
                        return None # Usuário está banido, nega o login

                    return user # Senha correta e sem banimento, retorna o objeto User
                except exceptions.VerifyMismatchError:
                    return None # Senha incorreta
            return None # Usuário não encontrado ou não ativo

    def get_post_by_id(self, id):
        """Obtém um post pelo seu ID."""
        with self.get_db() as db:
            post = db.query(Post).filter(Post.id == id, Post.is_deleted == False).options(joinedload(Post.author_user).joinedload(UserDetails.user)).first()
            if post:
                if post.image_urls:
                    post.image_urls = json.loads(post.image_urls)
                else:
                    post.image_urls = []
            return post

    def get_interaction_by_id(self, interaction_id: int):
        """Obtém uma interação específica pelo ID, carregando o usuário."""
        with self.get_db() as db:
            return db.query(Interaction).options(joinedload(Interaction.user_who_interacted)).filter(
                Interaction.id == interaction_id
            ).first()

    def delete_post_by_id(self, id):
        """Deleta posts pelo seu ID"""
        with self.get_db() as db:
            post = db.query(Post).filter(Post.id == id, Post.is_deleted == False).first()
            if post:
                post.is_deleted = True
                db.commit()
                return True
            return False
    
    def delete_interaction_by_id(self, interaction_id):
        """Deleta posts pelo seu ID"""
        with self.get_db() as db:
            interaction = db.query(Interaction).filter(Interaction.id == interaction_id, Interaction.is_deleted == False).first()
            if interaction:
                interaction.is_deleted = True # Corrigido: atualiza o campo correto
                db.commit()
                return True
            return False

    def toggle_post_reaction(self, user_id: int, post_id: int, reaction_type: str):
        """
        Registra, atualiza ou remove uma reação (like/dislike) a um post.
        reaction_type pode ser 'like_post' ou 'dislike_post'.
        """
        with self.get_db() as db:
            # 1. Verificar se o usuário já tem uma reação a este post
            existing_reaction = db.query(Interaction).filter(
                Interaction.user_id == user_id,
                Interaction.post_id == post_id,
                Interaction.type.in_(['like_post', 'dislike_post']), 
                Interaction.parent_interaction_id == None # Apenas reações diretas ao post
            ).first()

            if existing_reaction:
                if existing_reaction.type == reaction_type:
                    # Se a reação existente for do mesmo tipo, o usuário está "desfazendo" a reação.
                    db.delete(existing_reaction)
                    db.commit()
                    return True, ""
                else:
                    # Se a reação existente for de um tipo diferente, o usuário está "trocando" a reação.
                    existing_reaction.type = reaction_type
                    existing_reaction.timestamp = datetime.now() # Atualiza o timestamp da interação
                    db.commit()
                    return True, reaction_type
            else:
                # Se não houver reação existente, crie uma nova.
                success, result = self._register_interaction(user_id, post_id, reaction_type, None, None)
                if not success:
                    return False, result
                return True, reaction_type

    def toggle_comment_reaction(self, user_id: int, comment_id: int, reaction_type: str):
        """
        Registra, atualiza ou remove uma reação (like/dislike) a um comentário.
        reaction_type pode ser 'like_comment' ou 'dislike_comment'.
        """
        with self.get_db() as db:
            comment_target = db.query(Interaction).filter(
                Interaction.id == comment_id, 
                Interaction.type.in_(['comment_post', 'reply_comment'])
            ).first()

            if not comment_target:
                return False, "Comentário alvo não encontrado ou inválido."

            existing_reaction = db.query(Interaction).filter(
                Interaction.user_id == user_id,
                Interaction.parent_interaction_id == comment_id,
                Interaction.type.in_(['like_comment', 'dislike_comment']) 
            ).first()

            if existing_reaction:
                if existing_reaction.type == reaction_type:
                    # Se a reação existente for do mesmo tipo, o usuário está "desfazendo" a reação.
                    db.delete(existing_reaction)
                    db.commit()
                    return True, "Reação ao comentário removida com sucesso!"
                else:
                    # Se a reação existente for de um tipo diferente, o usuário está "trocando" a reação.
                    existing_reaction.type = reaction_type
                    existing_reaction.timestamp = datetime.now()
                    db.commit()
                    return True, f"Reação ao comentário alterada para '{reaction_type}' com sucesso!"
            else:
                # Se não houver reação existente, crie uma nova.
                success, result = self._register_interaction(user_id, comment_target.post_id, reaction_type, None, comment_id)
                if not success:
                    return False, result
                return True, f"Reação '{reaction_type}' ao comentário registrada com sucesso!"

    def register_reply_to_comment(self, user_id: int, parent_comment_id: int, reply_text: str):
        """Registra uma resposta a um comentário existente."""
        with self.get_db() as db:
            parent_comment = db.query(Interaction).filter(Interaction.id == parent_comment_id, Interaction.type.in_(['comment_post', 'reply_comment'])).first()
            if not parent_comment:
                return False, "Comentário não encontrado ou não é um comentário válido para responder."
            
            if parent_comment.type == "reply_comment":
                parent_comment_id = parent_comment.parent_interaction_id
                reply_text = f"@{parent_comment.user_who_interacted.id} {reply_text}" # Marca o usuário original da resposta

            post_id = parent_comment.post_id

            success, result = self._register_interaction(user_id, post_id, "reply_comment", reply_text, parent_comment_id)
            if not success:
                return False, result
            return True, result

    def get_comments_for_post(self, post_id: int):
        """Obtém todos os comentários e suas respostas para um dado post."""
        with self.get_db() as db:
            comments = db.query(Interaction).options(
                joinedload(Interaction.user_who_interacted), # Pega o usuário que fez o comentário
                joinedload(Interaction.child_interactions).joinedload(Interaction.user_who_interacted) # Pega respostas e likes do comentário e seus usuários
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None # Apenas comentários de nível superior
            ).order_by(Interaction.timestamp).all() # Ordena por data

            return comments

    def get_comment_by_id(self, comment_id: int):
        """Obtém um comentário específico (e suas respostas e likes)."""
        with self.get_db() as db:
            comment = db.query(Interaction).options(
                joinedload(Interaction.user_who_interacted),
                joinedload(Interaction.child_interactions).joinedload(Interaction.user_who_interacted)
            ).filter(Interaction.id == comment_id, Interaction.type == 'comment_post').first()
            return comment
    
    def count_reactions_for_post(self, post_id: int, reaction_type: str):
        """Conta o número de likes/dislikes para um post."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.post_id == post_id,
                Interaction.type == reaction_type,
                Interaction.parent_interaction_id == None # Apenas reações diretas ao post
            ).count()

    def count_comments_for_post(self, post_id: int):
        """Conta o número de comentários para um post específico."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None # Apenas comentários de nível superior
            ).count()

    def count_reactions_for_comment(self, comment_id: int, reaction_type: str):
        """Conta o número de likes/dislikes para um comentário."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.parent_interaction_id == comment_id,
                Interaction.type == reaction_type
            ).count()

    def get_user_post_reaction(self, user_id: int, post_id: int):
        """Obtém a reação do usuário a um post."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.user_id == user_id,
                Interaction.post_id == post_id,
                Interaction.type.in_(['like_post', 'dislike_post']),
                Interaction.parent_interaction_id == None
            ).first()

    def get_user_comment_reaction(self, user_id: int, comment_id: int):
        """Obtém a reação (like/dislike) de um usuário a um comentário ou resposta."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.user_id == user_id,
                Interaction.parent_interaction_id == comment_id, # Associa a um comentário/resposta pai
                Interaction.type.in_(['like_comment', 'dislike_comment']) 
            ).first()

    # Método para obter comentários paginados por like
    def get_paginated_comments(self, post_id, offset=0, limit=5):
        # Subconsulta para contar os likes de cada comentário
        with self.get_db() as db:
            likes_count_subquery = db.query( # Conta quantas Interaction.id existem para Interaction.parent_interaction_id
                Interaction.parent_interaction_id, 
                func.count(Interaction.id).label('num_likes')
            ).filter(
                Interaction.type == 'like_comment',
                Interaction.post_id == post_id
            ).group_by(Interaction.parent_interaction_id).subquery() # Agrupa por Interaction.parent_interaction_id para contar os likes de cada comentário

            dislikes_count_subquery = db.query(
                Interaction.parent_interaction_id,
                func.count(Interaction.id).label('num_dislikes')
            ).filter(
                Interaction.type == 'dislike_comment',
                Interaction.post_id == post_id
            ).group_by(Interaction.parent_interaction_id).subquery()
            
            replies_count_subquery = db.query(
                Interaction.parent_interaction_id,
                func.count(Interaction.id).label('num_replies')
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'reply_comment'
            ).group_by(Interaction.parent_interaction_id).subquery()

            # Query principal para buscar os comentários
            comments = db.query(
                Interaction, # Inclui a tabela de Interação
                func.coalesce(likes_count_subquery.c.num_likes, 0).label('num_likes'), # Coalesce para garantir que comentários sem likes retornem 0, sem isso o LEFT JOIN retornaria None. Label é o nome da coluna.
                func.coalesce(dislikes_count_subquery.c.num_dislikes, 0).label('num_dislikes'),
                func.coalesce(replies_count_subquery.c.num_replies, 0).label('num_replies')
            ).options(
                joinedload(Interaction.user_who_interacted)
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None # Apenas comentários de nível superior
            ).outerjoin( # Usa OUTER JOIN para garantir que comentários sem likes ainda sejam retornados. Se fosse INNER JOIN, comentários sem likes seriam excluídos.
                likes_count_subquery, 
                Interaction.id == likes_count_subquery.c.parent_interaction_id # A condição de junção é que o ID do comentário deve corresponder ao parent_interaction_id da subconsulta
            ).outerjoin(
                dislikes_count_subquery,
                Interaction.id == dislikes_count_subquery.c.parent_interaction_id
            ).outerjoin(
                replies_count_subquery,
                Interaction.id == replies_count_subquery.c.parent_interaction_id
            ).order_by(
                desc('num_likes'), # Ordena pelos likes, do maior para o menor
                desc(Interaction.timestamp) # Critério de desempate
            ).offset(offset).limit(limit).all()
            
            return comments
        
    # Método para obter comentários paginados por like
    def get_paginated_replies(self, post_id, comment_id, offset=0, limit=5):
        # Subconsulta para contar os likes de cada resposta
        with self.get_db() as db:
            likes_count_subquery = db.query(
                Interaction.parent_interaction_id,
                func.count(Interaction.id).label('num_likes')
            ).filter(
                Interaction.type == 'like_comment',
                Interaction.post_id == post_id
            ).group_by(Interaction.parent_interaction_id).subquery()

            dislikes_count_subquery = db.query(
                Interaction.parent_interaction_id,
                func.count(Interaction.id).label('num_dislikes')
            ).filter(
                Interaction.type == 'dislike_comment',
                Interaction.post_id == post_id
            ).group_by(Interaction.parent_interaction_id).subquery()

            # Query principal para buscar as respostas/replies
            replies = db.query(
                Interaction, # Inclui a tabela de Interação
                func.coalesce(likes_count_subquery.c.num_likes, 0).label('num_likes'), # Coalesce para garantir que respostas sem likes retornem 0, sem isso o LEFT JOIN retornaria None. Label é o nome da coluna.
                func.coalesce(dislikes_count_subquery.c.num_dislikes, 0).label('num_dislikes')
            ).options(
                joinedload(Interaction.user_who_interacted)
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'reply_comment',
                Interaction.parent_interaction_id == comment_id # Reply do comentário específico
            ).outerjoin( # Usa OUTER JOIN para garantir que respostas sem likes ainda sejam retornados. Se fosse INNER JOIN, respostas sem likes seriam excluídos.
                likes_count_subquery, 
                Interaction.id == likes_count_subquery.c.parent_interaction_id # A condição de junção é que o ID da resposta deve corresponder ao parent_interaction_id da subconsulta
            ).outerjoin(
                dislikes_count_subquery,
                Interaction.id == dislikes_count_subquery.c.parent_interaction_id
            ).order_by(
                desc('num_likes'), # Ordena pelos likes, do maior para o menor
                desc(Interaction.timestamp) # Critério de desempate
            )
            
            if limit and limit > 0:
                replies = replies.offset(offset).limit(limit)
            
            replies = replies.all()
            return replies
    
    def get_posts_with_most_likes(self, offset: int = 0, limit: int = 10):
        with self.get_db() as db:
            return db.query(Post).filter(Post.is_deleted == False).options(joinedload(Post.author_user).joinedload(UserDetails.user)).offset(offset).limit(limit).all()
    
    def get_comment_amount_for_post(self, post_id: int):
        """Conta o número de comentários para um post específico."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None # Apenas comentários de nível superior
            ).count()

    def get_reply_amout_for_comment(self, post_id: int, comment_id: int):
        """Conta o número de respostas para um comentário específico."""
        with self.get_db() as db:
            return db.query(Interaction).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'reply_comment',
                Interaction.parent_interaction_id == comment_id
            ).count()

    def get_user_posts(self, user_id):
        with self.get_db() as db:
            posts = db.query(Post).filter(Post.user_id == user_id).options(joinedload(Post.author_user).joinedload(UserDetails.user)).order_by(Post.created_at.desc()).all()
            return posts

    def get_user_comments_n_replies(self, user_id):
        with self.get_db() as db:
            interactions = db.query(Interaction).filter(Interaction.user_id == user_id, Interaction.type.in_(['reply_comment', 'comment_post'])).order_by(Interaction.timestamp.desc()).all()
            return interactions
    
    def check_and_update_user_penalties(self, user_id: int):
        with self.get_db() as db:
            now = datetime.now()

            db.query(ModerationHistory).filter(
                ModerationHistory.user_id == user_id,
                ModerationHistory.is_active == True,
                ModerationHistory.end_date != None,
                ModerationHistory.end_date < now
            ).update({"is_active": False}, synchronize_session=False)
            db.commit()

            return db.query(ModerationHistory).filter(
                ModerationHistory.user_id == user_id,
                ModerationHistory.is_active == True
            ).all()
