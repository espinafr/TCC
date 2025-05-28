import sqlite3
from datetime import datetime, timedelta
from argon2 import PasswordHasher

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
            c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, email TEXT UNIQUE, password TEXT, gender TEXT, creation_date TEXT, active INTEGER)''')
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

    def logto_user(self, login, password):
        with self.connect() as conn:
            c = conn.cursor
            user = self.get_user(login)
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