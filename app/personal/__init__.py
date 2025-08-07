#app/personal/__init__.py
from flask import Blueprint

# Define el blueprint con nombre 'personal', nombre del módulo actual (__name__) 
# y la carpeta donde se encuentran las plantillas
personal_bp = Blueprint('personal', __name__, template_folder='templates/personal')

# Importa las rutas al final para evitar importaciones circulares
from app.personal import routes