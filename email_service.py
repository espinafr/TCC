from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, exc

class EmailService:
    def __init__(self, app):
        self.mail = Mail(app)
        self.serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

    def send_confirmation_email(self, email, confirm_url):
        msg = Message('Confirme seu E-mail - Conexão em Família', 
                      sender=self.app.config['MAIL_USERNAME'], 
                      recipients=[email])
        msg.body = f'Olá! Clique no link para confirmar seu e-mail: {confirm_url}\nO link expira em 1 hora.'
        try:
            self.mail.send(msg)
            return True, None
        except Exception as e:
            return False, str(e)

    def generate_token(self, email):
        return self.serializer.dumps(email, salt='email-confirm')

    def verify_token(self, token, max_age=3600):
        try:
            email = self.serializer.loads(token, salt='email-confirm', max_age=max_age)
            return True, email
        except exc.SignatureExpired:
            return False, "O link de confirmação expirou"
        except Exception:
            return False, "Link inválido"