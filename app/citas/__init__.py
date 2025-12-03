from flask import Blueprint

#from .enfermeria_routes import bp as citas_bp

# BLUEPRINT PRINCIPAL
citas_bp = Blueprint('citas', __name__, template_folder='templates')

# Importar sub-rutas
from app.citas import  enfermeria_routes , archivo_routes