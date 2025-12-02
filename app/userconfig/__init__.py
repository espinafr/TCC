from flask import Blueprint

bp = Blueprint('userconfig', __name__)

from app.userconfig import routes