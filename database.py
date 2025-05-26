import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def connect(self):
        return sqlite3.connect(self.db_name)

    def init_users_db(self):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT UNIQUE, password TEXT, gender TEXT, creation_date TEXT, confirmed INTEGER)''')
            conn.commit()

    def save_user(self, email, password, confirmed=0):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT email FROM users WHERE email = ?', (email,))
            if c.fetchone():
                return False, "E-mail já registrado"
            c.execute('INSERT INTO users (name, email, password, gender, creation_date, confirmed) VALUES (?, ?, ?)', (email, password, confirmed))
            conn.commit()
            return True, None

    def confirm_user(self, email):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET confirmed = 1 WHERE email = ?', (email,))
            conn.commit()

    def check_user(self, email, password):
        with self.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT confirmed FROM users WHERE email = ? AND password = ?', (email, password))
            result = c.fetchone()
            return result[0] if result else None

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