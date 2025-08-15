from app.farmacia import farmacia_bp
from flask import render_template
from app.utils.helpers import roles_required, usuarios_con_rol_requerido

@farmacia_bp.route('/')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def index():
    return render_template('farmacia/index.html')
