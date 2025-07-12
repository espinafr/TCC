import os
from datetime import datetime, timedelta
from argon2 import PasswordHasher, exceptions
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
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
    gender = Column(String(1)) # Ajuste o tamanho conforme necessário
    creation_date = Column(DateTime, default=datetime.now) # SQLAlchemy gerencia DateTime objetos
    active = Column(Boolean, default=False) # 0/1 vira False/True

    # Relacionamentos
    posts = relationship("Post", back_populates="author_user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), ForeignKey('users.username'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    tag = Column(String(12))
    optional_tags = Column(String(75))
    created_at = Column(DateTime, default=datetime.now)
    image_urls = Column(Text, nullable=True) 

    # Relacionamento com User
    author_user = relationship("User", back_populates="posts")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', email='{self.email}')>"


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

    # Helper para obter usuário de forma consistente
    def _get_user_by_field(self, db, field_name: str, value):
        if field_name == 'email':
            return db.query(User).filter(User.email == value).first()
        elif field_name == 'username':
            return db.query(User).filter(User.username == value).first()
        elif field_name == 'id':
            return db.query(User).filter(User.id == value).first()
        return None

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
                # Isso ainda é importante para pegar falhas de UniqueConstraint
                # em caso de race conditions ou se a validação externa falhou por algum motivo.
                # "users_email_key" é um nome de constraint comum para unique(email) no PostgreSQL.
                if "users_email_key" in str(e) or "duplicate key value violates unique constraint" in str(e):
                    return False, "O email já está registrado."
                # Se o username fosse UNIQUE, você adicionaria uma verificação similar aqui.
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
            # update retorna o número de linhas afetadas
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

    def save_post(self, username, title, content, tag, optional_tags, image_urls_list=None):
        """Salva um novo post no banco de dados."""
        with self.get_db() as db:
            image_urls_json = json.dumps(image_urls_list) if image_urls_list else None

            try:
                new_post = Post(
                    username=username,
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
            post = db.query(Post).filter(Post.id == id).first()
            if post:
                if post.image_urls:
                    post.image_urls = json.loads(post.image_urls)
                else:
                    post.image_urls = []
            return post