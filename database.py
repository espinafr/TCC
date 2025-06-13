import sqlite3
from datetime import datetime, timedelta
from argon2 import PasswordHasher, exceptions

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def connect(self):
        return sqlite3.connect(self.db_name)

    def get_user(self, type: str, value):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute(f'SELECT * FROM users WHERE {type} = ?', (value,))
            result = c.fetchone()
            return result if result else False

    def init_users_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      username TEXT, 
                      email TEXT UNIQUE, 
                      password TEXT, 
                      gender TEXT, 
                      creation_date TEXT, 
                      active INTEGER
                      )''')
            conn.commit()
    
    def init_posts_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS posts (
                        post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        tags TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (email) REFERENCES users(email)
                        )''')
            conn.commit()
        
    def init_interactions_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS interactions (
                        interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        post_id INTEGER,
                        interaction_type TEXT, -- 'like', 'view', 'comment', 'share'
                        comment_text TEXT, -- NULL se não for comentário
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (email) REFERENCES users(email),
                        FOREIGN KEY (post_id) REFERENCES posts(post_id)
                        )''')
            conn.commit()

    def check_user_activation(self, _type, identification):
        userData = self.get_user(_type, identification)
        if userData:
            if userData[-1] == 0:
                diferencaTempo = datetime.now() - datetime.strptime(userData[-2], '%d-%m-%Y %H:%M:%S')
                if diferencaTempo > timedelta(hours=1):
                    contaDeletada = self.delete_user(userData[2])
                    if contaDeletada.rowcount == 0:
                        return False, "Erro manejando contas. Tente novamente."
                else:
                    return False, f"Já existe uma conta com \"{identification}\" em processo de ativação. Faltam {60 - int(diferencaTempo.total_seconds() / 60)} minutos"
            else:
                return False, f"Conta com \"{identification}\" já registrada."
        return True, True

    def save_user(self, username, email, password, gender, active=0):
        with self.connect() as conn:
            c = conn.cursor()

            data = {
                'email': email,
                'username': username
            }
            for _type in data:
                available = self.check_user_activation(_type, data[_type])
                if not available[0]:
                    return False, available[1]
            
            ph = PasswordHasher()
            password = ph.hash(password)
            c.execute('INSERT INTO users (username, email, password, gender, creation_date, active) VALUES (?, ?, ?, ?, ?, ?)', (username, email, password, gender, datetime.now().strftime('%d-%m-%Y %H:%M:%S'), active))
            conn.commit()
            return True, None

    def delete_user(self, email):
        with self.connect() as conn:
            c = conn.cursor()
            result = c.execute('DELETE FROM users WHERE email = ?', (email, ))
            conn.commit()
            return result

    def activate_user(self, email):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET active = 1 WHERE email = ?', (email,))
            conn.commit()

    def logto_user(self, login, password, _type):
        user = self.get_user(_type, login)
        if user:
            ph = PasswordHasher()
            try:
                ph.verify(user[3], password)
                return 1
            except exceptions.VerifyMismatchError:
                return None
        return None

    def save_post(self, email, title, content, tags):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO posts (email, title, content, tags) VALUES (?, ?, ?, ?)',
                    (email, title, content, ','.join(tags)))
            conn.commit()
            return c.lastrowid

    def register_interaction(self, email, post_id, interaction_type, comment_text=None):
        with sqlite3.connect(self.db_name) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO interactions (email, post_id, interaction_type, comment_text) VALUES (?, ?, ?, ?)',
                    (email, post_id, interaction_type, comment_text))
            conn.commit()

    def get_user_interactions(self, email):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT post_id, interaction_type FROM interactions WHERE email = ?', (email,))
            return [{'post_id': row['post_id'], 'type': row['interaction_type']} for row in c.fetchall()]

    def get_all_interactions(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT email, post_id, interaction_type FROM interactions')
            return [{'email': row['email'], 'post_id': row['post_id'], 'type': row['interaction_type']} for row in c.fetchall()]

    def get_post_by_id(self, post_id):
        with sqlite3.connect(self.db_name) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM posts WHERE post_id = ?', (post_id,))
            row = c.fetchone()
            return dict(row) if row else None