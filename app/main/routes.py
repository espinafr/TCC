from flask import render_template, session
from app.main import bp

@bp.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', login=session.get('id'))