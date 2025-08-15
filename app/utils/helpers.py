from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user, login_required

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'txt', 'jpg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def roles_required(roles):
    """
    Decorador para proteger rutas según roles permitidos.
    :param roles: lista o string con roles permitidos
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Normaliza a lista
            allowed_roles = roles if isinstance(roles, list) else [roles]

            # Obtiene el nombre real del rol del usuario
            rol_actual = getattr(current_user.rol, 'nombre_rol', None)

            # Depuración
            print("Roles permitidos:", allowed_roles)
            print("Rol actual:", rol_actual)

            # Validación
            if rol_actual not in allowed_roles:
                flash("No tienes permiso para acceder a esta sección.", "danger")
                return redirect(url_for('main.home'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def usuarios_con_rol_requerido(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.rol or current_user.rol == '':
            flash("Tu usuario no tiene un rol asignado para acceder.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
