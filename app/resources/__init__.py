from flask import Blueprint

bp = Blueprint('resources', __name__, template_folder='templates', static_folder='public')

from app.resources import routes
