from flask import Blueprint

bp = Blueprint('authentication', __name__)

from app.main import routes