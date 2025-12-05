from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, RadioField, TextAreaField, FileField, SelectField, MultipleFileField, DateField, BooleanField
from wtforms.validators import InputRequired, DataRequired, Email, Length, ValidationError, Optional
from flask_wtf.file import FileAllowed, FileSize
from werkzeug.datastructures import FileStorage
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
    selected_files = [f for f in field.data if isinstance(f, FileStorage) and f.filename]

    if len(selected_files) > 5:
        raise ValidationError('Você pode enviar no máximo 5 fotos.')


def validate_attachments(form, field):
    # Filtra arquivos efetivamente enviados
    selected_files = [f for f in field.data if isinstance(f, FileStorage) and f.filename]
    if len(selected_files) > 3:
        raise ValidationError('Você pode enviar no máximo 3 arquivos anexos (PDF ou imagens).')
    # opcional: tamanho máximo por arquivo já é verificado via FileSize ao definir o campo

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
    if not re.match(r'^[a-z0-9_]+$', field.data):
        raise ValidationError('O nome de usuário só pode conter letras minúsculas, números e underline (_), sem acentos.')

def validate_login(form, field):
    if not field.data:
        raise ValidationError('O login é obrigatório.')
    if '@' in field.data:
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', field.data):
            raise ValidationError('E-mail inválido.')
    else:
        if len(field.data) < 3 or len(field.data) > 15:
            raise ValidationError('O nome de usuário precisa ter de 3 a 15 caracteres.')
        if not re.match(r'^[a-z0-9_]+$', field.data):
            raise ValidationError('O nome de usuário só pode conter letras minúsculas, números e underline (_), sem acentos.')

class RegistrationForm(FlaskForm):
    email = StringField('E-mail', validators=[
        InputRequired(message='O e-mail é obrigatório.'),
        Email(message='Por favor, insira um e-mail válido.')
    ])
    username = StringField('Nome de Usuário', validators=[
        InputRequired(message='O nome de usuário é obrigatório.'),
        validate_username
    ])
    password = PasswordField('Senha', validators=[
        InputRequired(message='A senha é obrigatória.'),
        Length(min=8, max=30, message='A senha deve ter entre 8 e 30 caracteres.')
    ])

class LoginForm(FlaskForm):
    login = StringField('E-mail ou Nome de Usuário', validators=[
        InputRequired(message='O login é obrigatório.'),
        validate_login
    ])
    password = PasswordField('Senha', validators=[
        InputRequired(message='A senha é obrigatória.'),
        Length(min=8, max=30, message='A senha deve ter entre 8 e 30 caracteres.')
    ])

class PostForm(FlaskForm):
    tituloInput = StringField(name='tituloInput', validators=[InputRequired(message='O título é obrigatório.'), Length(min=5, max=100, message="O título precisa conter entre %(min)d e %(max)d caracteres")])
    contentTextarea = TextAreaField(name='contentTextarea', validators=[InputRequired(message='O conteúdo é obrigatório.'), Length(min=30, max=2000, message="O conteúdo precisa conter entre %(min)d e %(max)d caracteres")])
    tags = SelectField(name='tags', choices=[
        ("Desenho Infantil", "Desenho Infantil"), ("Educação", "Educação"), ("Saúde", "Saúde"), ("Disciplina", "Disciplina"), ("Nutrição", "Nutrição"), ("Comportamento", "Comportamento"), ("Lazer", "Lazer"), ("Tecnologia", "Tecnologia"), ("Família", "Família"), ("Desafios", "Desafios"), ("Desafio Semanal", "Desafio Semanal")
    ], validators=[InputRequired(message='Selecione uma categoria.'), validate_not_empty_choice], render_kw={'data-placeholder': 'true'})
    hiddenOptionalTags = StringField(validators=[Optional(), validate_opcional])
    inputFiles = MultipleFileField(
        'Enviar Fotos (até 5, max. 10MB cada)', #label
        validators=[
            Optional(), # O campo é opcional
            FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'jfif'], 'Apenas imagens JPG, PNG, JPEG e WEBP são permitidas!'),
            FileSize(max_size=10 * 1024 * 1024, message='O tamanho do arquivo não pode exceder 10MB!'),
            validate_fotos
        ]
    )


class ResourceForm(FlaskForm):
    tituloInput = StringField(name='tituloInput', validators=[InputRequired(message='O título é obrigatório.'), Length(min=5, max=150, message="O título precisa conter entre %(min)d e %(max)d caracteres")])
    category = SelectField(name='category', choices=[(c, c) for c in ALLOWED_CATEGORIES], validators=[InputRequired(message='Selecione uma categoria.'), validate_not_empty_choice])
    tags = StringField(validators=[Optional(), validate_opcional])
    contentTextarea = TextAreaField(name='contentTextarea', validators=[InputRequired(message='O conteúdo é obrigatório.'), Length(min=10, max=5000, message="O conteúdo precisa conter entre %(min)d e %(max)d caracteres")])
    bannerImage = FileField('Banner (opcional)', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'jfif'], 'Apenas imagens JPG, PNG, JPEG e WEBP são permitidas!'), FileSize(max_size=5 * 1024 * 1024, message='O tamanho do banner não pode exceder 5MB!')])
    attachments = MultipleFileField('Anexos (até 3, PDF ou imagens)', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'jfif', 'pdf'], 'Apenas imagens e PDFs são permitidos!'), FileSize(max_size=15 * 1024 * 1024, message='Cada arquivo não pode exceder 15MB!'), validate_attachments])
    youtubeUrl = StringField(name='youtubeUrl', validators=[Optional(), Length(max=255)])

    def validate_youtubeUrl(form, field):
        # Accept empty, or common YouTube URLs (youtu.be or youtube.com/watch?v=).
        if not field.data:
            return
        val = field.data.strip()
        # Simple regex to validate youtube url and capture id
        import re
        match = re.match(r'^(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_\-]{11})(?:[&?].*)?$', val)
        if not match:
            raise ValidationError('Insira uma URL do YouTube válida (ex: https://youtu.be/VIDEO_ID ou https://www.youtube.com/watch?v=VIDEO_ID).')
        # Replace the field value with embeddable URL
        video_id = match.group(1)
        field.data = f'https://www.youtube.com/embed/{video_id}'

def tiposDenuncia(form, field):
    if field.data not in ('interacao', 'usuario', 'post'):
        raise ValidationError("Categoria inválida")

class ReportForm(FlaskForm):
    category = RadioField('Category', validators=[InputRequired(message='Uma categoria de denúncia é obrigatória.')],
                          choices=[('discursoOdio', 'Discurso de ódio'),
                                   ('infoPrivada', 'Espalhar informações privadas'),
                                   ('conteudoImproprio', 'Conteúdo impróprio'),
                                   ('segurancaInfantil', 'Segurança infantil'),
                                   ('abusoAssedio', 'Abuso/Assédio'),
                                   ('spam', 'Spam'),
                                   ('impersonacao', 'Falsidade ideológica')])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=300, message='A descrição não pode exceder 300 caracteres.')
    ])
    target_id = StringField('ID do denunciado', validators=[InputRequired(message='O ID do que esta sendo denunciado é obrigatório.')])
    type = StringField('Tipo do denunciado', validators=[InputRequired(message='O tipo do denunciado é obrigatório.'), tiposDenuncia])
    perpetrator_id = StringField('ID do perpetrador', validators=[InputRequired(message='O ID de quem fez a ofença é obrigatório.')])

class ModerationForm(FlaskForm):
    type = RadioField('Tipo', validators=[InputRequired(message='O tipo de ação de moderação é obrigatória.')],
                          choices=[('user', 'Usuário'),
                                   ('post', 'Post')])
    target_id = StringField('ID à ser moderado', validators=[InputRequired(message='O ID à ser moderado é obrigatório.')])
    reason = TextAreaField('Razão', validators=[InputRequired(message='O motivo da punição é obrigatória.'), Length(max=500, message='O motivo não pode exceder 500 caracteres.')])
    end_date = DateField('Data de fim', validators=[Optional()])
    mod_action = RadioField('Ação de moderação', validators=[InputRequired(message='A ação de moderação é obrigatória.')],
                          choices=[('silenciar', 'Silenciar'),
                                   ('advertir', 'Advertir'),
                                   ('desativar', 'Desativar'),
                                   ('banir', 'Banir'),
                                   ('deletar', 'Deletar post'),
                                   ('desativar', 'Desativar post'),
                                   ('shadowban', 'Shadow-ban')])
class ProfileEditForm(FlaskForm):
    editDisplayName = StringField('Nome de Exibição', validators=[
        Optional(),
        Length(min=3, max=32, message='O nome de exibição deve ter entre 3 e 32 caracteres.')
    ])
    editBio = TextAreaField('Biografia', validators=[
        Optional(),
        Length(max=250, message='A biografia não pode exceder 250 caracteres.')
    ])
    editProfilePicInput = FileField('Foto de Perfil', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'jfif'], 'Apenas imagens JPG, PNG, JPEG e WEBP são permitidas!'),
        FileSize(max_size=5 * 1024 * 1024, message='O tamanho da foto de perfil não pode exceder 5MB!')
    ])
    editBannerInput = FileField('Banner', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg', 'webp', 'jfif'], 'Apenas imagens JPG, PNG, JPEG e WEBP são permitidas!'),
        FileSize(max_size=5 * 1024 * 1024, message='O tamanho do banner não pode exceder 5MB!')
    ])
    remove_banner = BooleanField('Remover Banner')
