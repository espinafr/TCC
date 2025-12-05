import requests
from flask import render_template
from itsdangerous import URLSafeTimedSerializer, exc

class EmailService:
    def __init__(self, app=None):
        self.api_key = None
        self.serializer = None
        self.app = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.api_key = app.config["RESEND_API_KEY"]
        self.from_email = app.config["RESEND_FROM"]
        self.serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        self.app = app

    def send_confirmation_email(self, email, nome, confirm_url):
        # renderiza seu template normalmente
        html_content = render_template(
            "emails/confirmation_email.html",
            confirmation_link=confirm_url
        )

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": self.from_email,
                    "to": email,
                    "subject": "Confirme seu E-mail - Timby",
                    "html": html_content
                }
            )

            if response.status_code >= 200 and response.status_code < 300:
                return True, None
            else:
                return False, f"Erro Resend: {response.text}"

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