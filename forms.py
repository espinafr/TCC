from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField
from wtforms.validators import DataRequired, Length

class PostForm(FlaskForm):
    title = StringField('Título', validators=[DataRequired(message='O título é obrigatório.'), Length(max=100)])
    content = TextAreaField('Conteúdo', validators=[DataRequired(message='O conteúdo é obrigatório.'), Length(max=1000)])
    tags = SelectMultipleField('Tags', choices=[
        ('esportes', 'Esportes'),
        ('arte', 'Arte'),
        ('leitura', 'Leitura'),
        ('ao_ar_livre', 'Ao Ar Livre'),
        ('educativo', 'Educativo')
    ], validators=[DataRequired(message='Selecione uma categoria.')])