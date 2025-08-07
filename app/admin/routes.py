#app/admin/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.utils.db import db
from app.models.personal import Usuario, Roles  # Correcto: import desde models
from werkzeug.security import generate_password_hash
from app.utils.helpers import login_required
from sqlalchemy.exc import SQLAlchemyError

#bp = Blueprint('admin', __name__, template_folder='templates/admin')
bp = Blueprint('admin', __name__)

# Obtener el ID del usuario actual en sesión
def obtener_id_usuario_actual():
    if 'usuario' in session:
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        return usuario.id_usuario if usuario else None
    return None


# Panel de administración
@bp.route('/')
@login_required(roles='Administrador')
def panel():
    return render_template('admin/admin.html', usuario=session['usuario'])


@bp.route('/usuarios')
@login_required(roles='Administrador')
def lista_usuarios():
    usuarios = Usuario.query.order_by(Usuario.id_usuario).all()  # Cambia 'id_usuario' por el nombre correcto
    return render_template('admin/lista_usuarios.html', usuarios=usuarios)

# Editar usuario específico
@bp.route('/editar_usuario/<int:usuario_id>', methods=['GET', 'POST'])
@login_required(roles='Administrador')
def editar_usuario(usuario_id):
    id_actual = obtener_id_usuario_actual()
    if usuario_id == id_actual:
        flash('No puedes editar tu propio usuario desde aquí.', 'warning')
        return redirect(url_for('admin.lista_usuarios'))

    usuario = Usuario.query.get_or_404(usuario_id)
    roles = Roles.query.all()

    if request.method == 'POST':
        nuevo_rol = request.form.get('rol')
        nueva_contra = request.form.get('contrasena')

        # Buscar el objeto de rol por nombre
        rol_obj = Roles.query.filter_by(nombre_rol=nuevo_rol).first()
        if not rol_obj:
            flash('Rol no válido.', 'danger')
            return redirect(url_for('admin.editar_usuario', usuario_id=usuario_id))

        usuario.rol_id = rol_obj.id_rol  # Asignar nuevo rol

        if nueva_contra:
            usuario.set_password(nueva_contra)

        try:
            db.session.commit()
            flash('Usuario actualizado correctamente.', 'success')
        except SQLAlchemyError:
            db.session.rollback()
            flash('Error al actualizar el usuario.', 'danger')

        return redirect(url_for('admin.lista_usuarios'))

    return render_template('admin/editar_usuario.html', usuario=usuario, roles=roles)

# Eliminar usuario
@bp.route('/eliminar_usuario/<int:usuario_id>', methods=['POST'])
@login_required(roles='Administrador')
def eliminar_usuario(usuario_id):
    id_actual = obtener_id_usuario_actual()
    if usuario_id == id_actual:
        flash('No puedes eliminar tu propio usuario.', 'warning')
        return redirect(url_for('admin.lista_usuarios'))

    usuario = Usuario.query.get(usuario_id)
    if usuario:
        try:
            db.session.delete(usuario)
            db.session.commit()
            flash('Usuario eliminado correctamente.', 'success')
        except SQLAlchemyError:
            db.session.rollback()
            flash('Error al eliminar el usuario.', 'danger')
    else:
        flash('Usuario no encontrado.', 'warning')

    return redirect(url_for('admin.lista_usuarios'))

#registrar los usuarios
@bp.route('/registrar_usuario', methods=['GET', 'POST'])
@login_required(roles='Administrador')
def registrar_usuario():
    if 'usuario' not in session or session.get('rol') != 'Administrador':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        usuario = request.form['usuario'].upper()
        contrasena = request.form['contrasena']
        nombre_rol = request.form['rol']

        if Usuario.query.filter_by(usuario=usuario).first():
            flash('El usuario ya existe.', 'warning')
            return redirect(url_for('admin.registrar_usuario'))

        rol_obj = Roles.query.filter_by(nombre_rol=nombre_rol).first()
        if not rol_obj:
            flash("Rol no válido", "danger")
            return redirect(url_for('admin.registrar_usuario'))

        nuevo_usuario = Usuario(usuario=usuario, rol_id=rol_obj.id_rol)
        nuevo_usuario.set_password(contrasena)

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Usuario registrado correctamente', 'success')
            return redirect(url_for('admin.panel'))
        except SQLAlchemyError:
            db.session.rollback()
            flash('Error al registrar usuario', 'danger')
            return redirect(url_for('admin.registrar_usuario'))

    roles = Roles.query.all()
    return render_template('admin/registrar_usuario.html', roles=roles)

