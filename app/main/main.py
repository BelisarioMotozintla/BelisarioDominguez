from flask import Blueprint, render_template, redirect, session, url_for
from app.models import Archivo
from . import main_bp  # Importamos el blueprint definido en __init__.py



bp = Blueprint('main', __name__, template_folder='templates')
from . import main_bp  # Importamos el blueprint definido en __init__.py

@main_bp.route('/')

@bp.route('/')
def home():
    #if 'usuario' not in session:
    #    return redirect(url_for('auth.login'))
	
    # Consulta con SQLAlchemy ordenando por fecha_subida descendente
    #archivos = Archivo.query.order_by(Archivo.fecha_subida.desc()).all()

    #return render_template('index.html', archivos=archivos, usuario=session['usuario'], es_admin=(session.get('rol') == 'admin'))
    #archivos = Archivo.query.order_by(Archivo.fecha_subida.desc()).all() if 'usuario' in session else []
    #return render_template('home.html', archivos=archivos, usuario=session.get('usuario'), es_admin=(session.get('rol') == 'admin'))
    return render_template('home.html')  # Asegúrate de tener `home.html` en templates	