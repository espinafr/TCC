import os
from datetime import datetime, timedelta
from argon2 import PasswordHasher, exceptions
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
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
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    gender = Column(String(1))
    creation_date = Column(DateTime, default=datetime.now)
    active = Column(Boolean, default=False)

    # Relacionamentos
    posts = relationship("Post", back_populates="author_user")
    interactions = relationship("Interaction", foreign_keys="[Interaction.user_id]", back_populates="user_who_interacted")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tag = Column(String(12))
    optional_tags = Column(String(75))
    created_at = Column(DateTime, default=datetime.now)
    image_urls = Column(Text, nullable=True) 

    # Relacionamentos
    author_user = relationship("User", back_populates="posts")
    interactions = relationship("Interaction", foreign_keys="[Interaction.post_id]", back_populates="post_being_interacted")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', username='{self.username}')>"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    parent_interaction_id = Column(Integer, ForeignKey('interactions.id'), nullable=True) 
    type = Column(String(50), nullable=False)  # 'like_post', 'dislike_post', 'comment_post', 'like_comment', 'dislike_comment', 'reply_comment', 'view_post', 'share_post'
    value = Column(String(300), nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

    # Relacionamentos
    user_who_interacted = relationship("User", back_populates="interactions", foreign_keys=[user_id])
    post_being_interacted = relationship("Post", back_populates="interactions", foreign_keys=[post_id])
    
    # Hierarquia de comentários
    parent_interaction = relationship("Interaction", remote_side=[id], back_populates="child_interactions")
    child_interactions = relationship("Interaction", back_populates="parent_interaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Interaction(id='{self.id}', post_id='{self.post_id}', user_id='{self.user_id}', type='{self.type}', parent_id={self.parent_interaction_id})>"

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
    def _get_user_by_field(self, db, field_name: str, value):
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
    
    def get_user(self, type: str, value):
        """Retorna um usuário pelo tipo (email, username, id) e valor."""
        with self.get_db() as db:
            user = self._get_user_by_field(db, type, value)
            return user if user else False

    def check_user_activation(self, _type, identification):
        """
        Verifica a ativação do usuário e lida com contas não ativas expiradas.
        Retorna (True, True) para sucesso, (False, mensagem) para erro/problema.
        """
        with self.get_db() as db:
            user_data = self._get_user_by_field(db, _type, identification)

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

    def save_user(self, username, email, password, gender, active=False):
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
                    gender=gender,
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
            result = db.query(User).filter(User.email == email).update({"active": True})
            db.commit()
            return result > 0 # Retorna True se o usuário foi encontrado e atualizado

    def logto_user(self, login, password, _type):
        """Verifica as credenciais do usuário para login."""
        with self.get_db() as db:
            user = self._get_user_by_field(db, _type, login)
            if user and user.active: # Apenas usuários ativos podem logar
                try:
                    self.ph.verify(user.password, password)
                    return user # Retorna o objeto User se o login for bem-sucedido
                except exceptions.VerifyMismatchError:
                    return None # Senha incorreta
            return None # Usuário não encontrado ou não ativo

    def save_post(self, user_id, title, content, tag, optional_tags, image_urls_list=None):
        """Salva um novo post no banco de dados."""
        with self.get_db() as db:
            image_urls_json = json.dumps(image_urls_list) if image_urls_list else None

            try:
                new_post = Post(
                    user_id=user_id,
                    title=title,
                    content=content,
                    tag=tag,
                    optional_tags=optional_tags,
                    image_urls=image_urls_json
                )
                db.add(new_post)
                db.commit()
                db.refresh(new_post) # Recarrega o objeto para ter o ID gerado pelo DB
                return new_post.id
            except Exception as e:
                db.rollback()
                print(f"Erro ao salvar post: {e}")
                return None

    def get_post_by_id(self, id):
        """Obtém um post pelo seu ID."""
        with self.get_db() as db:
            post = db.query(Post).options(joinedload(Post.author_user)).filter(Post.id == id).first()
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
                    return True, "Reação removida com sucesso!"
                else:
                    # Se a reação existente for de um tipo diferente, o usuário está "trocando" a reação.
                    existing_reaction.type = reaction_type
                    existing_reaction.timestamp = datetime.now() # Atualiza o timestamp da interação
                    db.commit()
                    return True, f"Reação alterada para '{reaction_type}' com sucesso!"
            else:
                # Se não houver reação existente, crie uma nova.
                success, result = self._register_interaction(user_id, post_id, reaction_type, None, None)
                if not success:
                    return False, result
                return True, result

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
            parent_comment = db.query(Interaction).filter(Interaction.id == parent_comment_id, Interaction.type == 'comment_post').first()
            if not parent_comment:
                return False, "Comentário não encontrado ou não é um comentário válido para responder."
            
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

    def get_comments_and_replies_for_post(self, post_id: int, user_id: int = None, limit: int = None, offset: int = None):
        """
        Retorna comentários e suas respostas para um post, com paginação,
        incluindo contagens de likes/dislikes e a reação do usuário logado.
        Prioriza os comentários do usuário logado.
        """
        with self.get_db() as db:
            # Primeiro, obter os comentários do usuário logado
            user_comments_query = db.query(Interaction).options(
                joinedload(Interaction.user_who_interacted)
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None,  # Comentários de nível superior
                Interaction.user_id == user_id  # Filtrar comentários do usuário
            ).order_by(Interaction.timestamp.desc())

            # Depois, obter os outros comentários
            other_comments_query = db.query(Interaction).options(
                joinedload(Interaction.user_who_interacted)
            ).filter(
                Interaction.post_id == post_id,
                Interaction.type == 'comment_post',
                Interaction.parent_interaction_id == None,  # Comentários de nível superior
                Interaction.user_id != user_id  # Excluir comentários do usuário
            ).order_by(Interaction.timestamp.desc())

            if offset is not None and limit is not None:
                # Aplicar paginação APENAS aos outros comentários (para não paginar os comentários do usuário)
                other_comments_query = other_comments_query.offset(offset).limit(limit)

            user_comments = user_comments_query.all()
            other_comments = other_comments_query.all()

            # Combinar os comentários do usuário e os outros comentários
            comments = user_comments + other_comments

            comments_data = []
            for comment in comments:
                # Contagens de likes/dislikes para o comentário
                likes_count = self.count_reactions_for_comment(comment.id, 'like_comment')
                dislikes_count = self.count_reactions_for_comment(comment.id, 'dislike_comment')

                # Reação do usuário ao comentário
                user_reaction = None
                if user_id:
                    user_reaction_obj = self.get_user_comment_reaction(user_id, comment.id)
                    if user_reaction_obj:
                        user_reaction = user_reaction_obj.type

                # Obter a resposta mais curtida (se houver)
                most_liked_reply = None
                replies = db.query(Interaction).options(joinedload(Interaction.user_who_interacted)).filter(
                    Interaction.parent_interaction_id == comment.id,
                    Interaction.type == 'reply_comment'
                ).all()

                if replies:
                    most_liked_reply = max(replies, key=lambda reply: self.count_reactions_for_comment(reply.id, 'like_comment') - self.count_reactions_for_comment(reply.id, 'dislike_comment'))
                    most_liked_reply_data = {
                        "id": most_liked_reply.id,
                        "username": most_liked_reply.user_who_interacted.username,
                        "content": most_liked_reply.value,
                        "likes": self.count_reactions_for_comment(most_liked_reply.id, 'like_comment'),
                        "dislikes": self.count_reactions_for_comment(most_liked_reply.id, 'dislike_comment'),
                        "user_reaction": self.get_user_comment_reaction(user_id, most_liked_reply.id).type if user_id and self.get_user_comment_reaction(user_id, most_liked_reply.id) else None
                    } if most_liked_reply else None

                comment_data = {
                    "id": comment.id,
                    "username": comment.user_who_interacted.username,
                    "content": comment.value,
                    "likes": likes_count,
                    "dislikes": dislikes_count,
                    "user_reaction": user_reaction,
                    "replies": [most_liked_reply_data] if most_liked_reply_data else []
                }
                comments_data.append(comment_data)

            return comments_data

    def get_interaction_by_id(self, interaction_id: int):
        """Obtém uma interação específica pelo ID, carregando o usuário."""
        with self.get_db() as db:
            return db.query(Interaction).options(joinedload(Interaction.user_who_interacted)).filter(
                Interaction.id == interaction_id
            ).first()
        
    def get_replies_for_comment(self, comment_id: int, user_id: int = None):
        """Obtém todas as respostas para um comentário específico."""
        with self.get_db() as db:
            replies = db.query(Interaction).options(joinedload(Interaction.user_who_interacted)).filter(
                Interaction.parent_interaction_id == comment_id,
                Interaction.type == 'reply_comment'
            ).all()

            replies_data = []
            for reply in replies:
                likes_count = self.count_reactions_for_comment(reply.id, 'like_comment')
                dislikes_count = self.count_reactions_for_comment(reply.id, 'dislike_comment')

                user_reaction = None
                if user_id:
                    user_reaction_obj = self.get_user_comment_reaction(user_id, reply.id)
                    if user_reaction_obj:
                        user_reaction = user_reaction_obj.type

                reply_data = {
                    "id": reply.id,
                    "username": reply.user_who_interacted.username,
                    "content": reply.value,
                    "likes": likes_count,
                    "dislikes": dislikes_count,
                    "user_reaction": user_reaction
                }
                replies_data.append(reply_data)

            return replies_data