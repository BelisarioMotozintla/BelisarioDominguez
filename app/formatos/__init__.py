#app/formatos/__init__.py
from flask import Blueprint
formatos_bp = Blueprint('formatos', __name__, template_folder='templates/formatos')
from app.formatos import formatos


