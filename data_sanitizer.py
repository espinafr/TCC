from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, RadioField #, IntegerField, SelectMultipleField
from wtforms.validators import DataRequired, Email, Length, ValidationError # NumberRange,
import re

def validate_username(form, field):
    if not field.data:
        raise ValidationError('O nome de usuário é obrigatório.')
    if len(field.data) < 3 or len(field.data) > 15:
        raise ValidationError('O nome de usuário precisa ter de 3 a 15 caracteres.')
    if not field.data.isalnum() and '_' not in field.data:
        raise ValidationError('O nome de usuário só pode conter letras, números e underline.')

def validate_login(form, field):
    if not field.data:
        raise ValidationError('O login é obrigatório.')
    if '@' in field.data:
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', field.data):
            raise ValidationError('E-mail inválido.')
    else:
        if len(field.data) < 3 or len(field.data) > 15:
            raise ValidationError('O nome de usuário precisa ter de 3 a 15 caracteres.')
        if not field.data.isalnum() and '_' not in field.data:
            raise ValidationError('O nome de usuário só pode conter letras, números e underline.')

def validate_gender(form, field):
    if not field.data or field.data[0].lower() not in ['a', 'o', 'e']:
        raise ValidationError('Gênero inválido.')

class RegistrationForm(FlaskForm):
    email = StringField('E-mail', validators=[
        DataRequired(message='O e-mail é obrigatório.'),
        Email(message='Por favor, insira um e-mail válido.')
    ])
    username = StringField('Nome de Usuário', validators=[
        DataRequired(message='O nome de usuário é obrigatório.'),
        validate_username
    ])
    password = PasswordField('Senha', validators=[
        DataRequired(message='A senha é obrigatória.'),
        Length(min=8, max=20, message='A senha deve ter entre 8 e 20 caracteres.')
    ])
    gender = RadioField('Gênero', choices=[
        ('a', 'Feminino'),
        ('o', 'Masculino'),
        ('e', 'Outro')
    ], validators=[
        DataRequired(message='O gênero é obrigatório.'),
        validate_gender
    ])

class LoginForm(FlaskForm):
    login = StringField('E-mail ou Nome de Usuário', validators=[
        DataRequired(message='O login é obrigatório.'),
        validate_login
    ])
    password = PasswordField('Senha', validators=[
        DataRequired(message='A senha é obrigatória.'),
        Length(min=8, max=20, message='A senha deve ter entre 8 e 20 caracteres.')
    ])