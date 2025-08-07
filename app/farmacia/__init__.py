from flask import Blueprint
farmacia_bp = Blueprint('farmacia', __name__, template_folder='templates')
from app.farmacia import routes
