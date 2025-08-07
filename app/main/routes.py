from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return render_template('main/home.html')  # asegúrate de que exista este templateate	