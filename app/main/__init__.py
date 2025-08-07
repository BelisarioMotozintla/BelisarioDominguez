from flask import Blueprint
main_bp = Blueprint('main', __name__, template_folder='templates')
#from .main import bp as main_bp
from app.main.routes import bp

