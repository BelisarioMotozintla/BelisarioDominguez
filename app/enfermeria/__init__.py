from flask import Blueprint
enfermeria_bp = Blueprint('enfermeria', __name__, template_folder='templates/enfermeria')
from app.enfermeria import formulario

