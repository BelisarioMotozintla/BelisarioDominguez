from app.formatos import formatos_bp
from flask import render_template

@formatos_bp.route('/')
def index():
    return render_template('formatos/index.html')
