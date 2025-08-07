from functools import wraps
from flask import session, redirect, url_for, flash  

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'txt', 'jpg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(roles=None, session_key='usuario', login_route='auth.login'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session_key not in session:
                flash("Debes iniciar sesión para acceder.", "warning")
                return redirect(url_for(login_route, next=request.endpoint))
            
            if roles:
                if isinstance(roles, str):
                    roles_list = [roles]
                else:
                    roles_list = roles

                # Solo verifica roles si están en la sesión (asociados a `session_key`)
                if session_key == 'usuario' and session.get('rol') not in roles_list:
                    flash("No tienes permiso para acceder a esta sección.", "danger")
                    return redirect(url_for('main.home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator
