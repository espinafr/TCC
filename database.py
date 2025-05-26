import sqlite3
from datetime import datetime
from argon2 import PasswordHasher

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def connect(self):
        return sqlite3.connect(self.db_name)

    def get_user(self, email):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE email = ?', (email,))
            result = c.fetchone()
            return result if result else False

    def init_users_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT UNIQUE, password TEXT, gender TEXT, creation_date TEXT, confirmed INTEGER)''')
            conn.commit()

    def save_user(self, username, email, password, gender, confirmed=0):
        with self.connect() as conn:
            c = conn.cursor()
            if self.get_user(email):
                return False, "E-mail já registrado"
            ph = PasswordHasher()
            password = ph.hash(password)
            c.execute('INSERT INTO users (username, email, password, gender, creation_date, confirmed) VALUES (?, ?, ?, ?, ?, ?)', (username, email, password, gender, datetime.now(), confirmed))
            conn.commit()
            return True, None

    def activate_user(self, email):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET confirmed = 1 WHERE email = ?', (email,))
            conn.commit()

    def check_user(self, email, password):
        with self.connect() as conn:
            c = conn.cursor
            user = self.get_user(email)
            if user:
                ph = PasswordHasher()
                if ph.verify(user[3], password):
                    return 1
            return None

    def init_missions_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS missions
                         (mission_id INTEGER PRIMARY KEY, description TEXT, age_min INTEGER, age_max INTEGER,
                          category TEXT, duration INTEGER, goal TEXT)''')
            missions = [
                (1, 'Criar uma história em família, cada um adicionando uma frase', 8, 13, 'criatividade', 30, 'fortalecer vínculo'),
                (2, 'Jogar uma partida de futebol no quintal', 10, 13, 'esportes', 45, 'reduzir tempo de tela'),
                (3, 'Ler um capítulo de um livro juntos', 8, 12, 'leitura', 20, 'estimular leitura'),
            ]
            c.executemany('INSERT OR IGNORE INTO missions VALUES (?, ?, ?, ?, ?, ?, ?)', missions)
            conn.commit()

    def get_mission(self, child_age, interests, available_time):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT description, duration FROM missions WHERE age_min <= ? AND age_max >= ? AND duration <= ? AND category IN ({})'.format(','.join(['?']*len(interests))),
                      [child_age, child_age, available_time] + interests)
            missions = c.fetchall()
            return missions