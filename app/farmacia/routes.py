from app.farmacia import farmacia_bp
from flask import render_template

@farmacia_bp.route('/')
def index():
    return render_template('farmacia/index.html')
