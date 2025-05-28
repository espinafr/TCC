import re

class Sanitizer:
    def __init__(self):
        self.valid_interests = ['esportes', 'arte', 'leitura']
    
    def validate_login(self, data: list):
        errors = []
        logintype = ''
        # Validar senha
        if not data.get('password') or len(data.get('password')) < 8 or len(data.get('password')) > 20:
            errors.append('A senha deve ter entre 8 e 20 caracteres.')
        # Validar e-mail ou nome
        if data.get('login'):
            if '@' in data.get('login'):
                logintype = 'email'
                if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', data.get('login')):
                    errors.append('E-mail inválido.')
            else:
                logintype = 'username'
                if re.search(r'[^\w]', data.get('login')) or len(data.get('login')) < 3 or len(data.get('login')) > 15:
                    errors.append('O nome de usuário precisa ter de 4 a 15 caracteres e só pode conter letras e underline')
        else:
            errors.append('Faltam dados.')
        return errors, logintype
    
    def validate_registration(self, data: list):
        errors = []
        # Validar senha
        if not data.get('password') or len(data.get('password')) < 8 or len(data.get('password')) > 20:
            errors.append('A senha deve ter entre 8 e 20 caracteres.')
        # Validar e-mail
        if not data.get('email') or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', data.get('email')):
            errors.append('E-mail inválido.')
        # Validar username7
        if not data.get('username') or re.search(r'[^\w]', data.get('username')) or len(data.get('username')) < 3 or len(data.get('username')) > 15:
            errors.append('O nome de usuário precisa ter de 4 a 15 caracteres e só pode conter letras e underline')
        # Validar gênero
        if not data.get('gender') or data.get('gender')[0] not in ['a', 'o', 'e']:
            errors.append('Gênero inválido.')
        
        return errors

    # Teste
    def validate_preferences(self, data):
        errors = []
        # Exemplo: validar apenas preferências
        child_age = data.get('child_age')
        if not child_age or not child_age.isdigit() or not (8 <= int(child_age) <= 13):
            errors.append('A idade da criança deve estar entre 8 e 13 anos.')
        interests = data.get('interests', [])
        if not interests:
            errors.append('Selecione pelo menos um interesse.')
        if not all(interest in self.valid_interests for interest in interests):
            errors.append('Interesse inválido.')
        return errors