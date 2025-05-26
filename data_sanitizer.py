import re

class Sanitizer:
    def __init__(self):
        self.valid_interests = ['esportes', 'arte', 'leitura']

    def validate_registration(self, data):
        errors = []
        # Validar username
        if not data.get('email') or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', data.get('email')):
            errors.append('O username precisa ter entre 3 e 15 caracteres')
        # Validar e-mail
        if not data.get('email') or not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', data.get('email')):
            errors.append('E-mail inválido.')
        # Validar senha
        if not data.get('password') or len(data.get('password')) < 8 or len(data.get('password')) > 20:
            errors.append('A senha deve ter entre 8 e 20 caracteres.')
        
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