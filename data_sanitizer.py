from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, RadioField, TextAreaField, SelectMultipleField, SelectField, MultipleFileField
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional
from flask_wtf.file import FileAllowed, FileSize
import re

ALLOWED_CATEGORIES = [
    'Amamentação',
    'Sono infantil',
    'Primeiros passos',
    'Fase escolar',
    'TDAH',
    'Autismo',
    'Alergias',
    'Gripe e resfriado',
    'Culinária kids',
    'Recusa alimentar',
    'Birras',
    'Bullying',
    'Desenho',
    'Música',
    'Leitura',
    'Contação histórias',
    'Jogos digitais',
    'Redes sociais',
    'Tempo de tela',
    'Limites',
    'Mesada',
    'Tarefas domésticas',
    'Divórcio',
    'Irmãos',
    'Avós',
    'Adoção',
    'Cyberbullying',
    'Sexualidade',
    'Puberdade',
    'Crise adolescência'
]

def validate_fotos(form, field):
    # Filtra arquivos que realmente foram selecionados (não são vazios)
    selected_files = [f for f in field.data if f and f.filename]

    if len(selected_files) > 5:
        raise ValidationError('Você pode enviar no máximo 5 fotos.')

def validate_not_empty_choice(form, field):
    if field.data == '':
        raise ValidationError('Por favor, selecione uma opção válida.')

def validate_opcional(form, field):
    if not field.data:
        field.data = []
        return

    input_categories = [cat.strip() for cat in field.data.split(',')] # string pra lista
    input_categories = list(filter(None, input_categories)) # remove itens vazios 
    unique_categories = list(set(input_categories)) # remove duplicatas

    MAX_CATEGORIES = 5
    if len(unique_categories) > MAX_CATEGORIES:
        raise ValidationError(f'Você pode selecionar no máximo {MAX_CATEGORIES} categorias.')

    for category in unique_categories:
        if category not in ALLOWED_CATEGORIES:
            raise ValidationError(f'A categoria "{category}" não é válida. Categorias permitidas: {", ".join(ALLOWED_CATEGORIES)}.')


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

class PostForm(FlaskForm):
    titulo = StringField(name='titulo', validators=[DataRequired(message='O título é obrigatório.'), Length(min=5, max=100, message="O título precisa conter entre %(min)d e %(max)d caracteres")])
    conteudo = TextAreaField(name='conteudo', validators=[DataRequired(message='O conteúdo é obrigatório.'), Length(min=30, max=1000, message="O conteúdo precisa conter entre %(min)d e %(max)d caracteres")])
    tags = SelectField(name='tags', choices=[
        ("desen_infan", "Desenho Infantil"), ("educacao", "Educação"), ("saude", "Saúde"), ("disciplina", "Disciplina"), ("nutricao", "Nutrição"), ("comportamen", "Comportamento"), ("lazer", "Lazer"), ("tecnologia", "Tecnologia"), ("familia", "Família"), ("desafios", "Desafios")
    ], validators=[DataRequired(message='Selecione uma categoria.'), validate_not_empty_choice], render_kw={'data-placeholder': 'true'})
    optionaltags = StringField(validators=[Optional(), validate_opcional])
    images = MultipleFileField(
        'Enviar Fotos (até 5, max. 10MB cada)', #label
        validators=[
            Optional(), # O campo é opcional
            FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Apenas imagens JPG, PNG, JPEG e WEBP são permitidas!'),
            FileSize(max_size=10 * 1024 * 1024, message='O tamanho do arquivo não pode exceder 10MB!'),
            validate_fotos
        ]
    )