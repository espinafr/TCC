from flask import render_template
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, exc

class EmailService:
    def __init__(self, app=None):
        self.mail = None
        self.serializer = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.mail = app.extensions.get('mail')
        if not self.mail:
            raise RuntimeError("A extensão Flask-Mail não foi inicializada corretamente.")
        self.serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        self.app = app

    def send_confirmation_email(self, email, nome, confirm_url):
        msg = Message('Confirme seu E-mail - Timby', 
                      sender=self.app.config['MAIL_USERNAME'], 
                      recipients=[email])
        msg.html = render_template('/emails/confirmation_email.html', confirmation_link=confirm_url)
        try:
            self.mail.send(msg)
            return True, None
        except Exception as e:
            return False, str(e)

    def generate_token(self, email):
        return self.serializer.dumps(email, salt='mAiL-ConnnnfirMMmmmmMMAaAation')

    def verify_token(self, token, max_age=3600):
        try:
            email = self.serializer.loads(token, salt="mAiL-ConnnnfirMMmmmmMMAaAation", max_age=max_age)
            return True, email
        except exc.SignatureExpired:
            return False, "O link de confirmação expirou"
        except Exception:
            return False, "Link inválido"