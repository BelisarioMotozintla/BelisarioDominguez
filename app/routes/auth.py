from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.db import db
from app.models import Usuario

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET'])
def home():
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            usuario = request.form['usuario'].upper()
            contrasena = request.form['contrasena']

            user = Usuario.query.filter_by(usuario=usuario).first()

            if user and user.check_password(contrasena):
                session['usuario'] = usuario
                session['rol'] = user.rol
                flash('Inicio de sesión exitoso', 'info')

                if user.rol == 'admin':
                    return redirect(url_for('admin.panel'))
                else:
                    return redirect(url_for('formulario.formulario'))
            else:
                flash('Credenciales incorrectas', 'error')
                return redirect(url_for('auth.login'))

        except Exception as e:
            print("Error durante login:", e)
            flash('Error interno del servidor', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/registrar_usuario', methods=['GET', 'POST'])
def registrar_usuario():
    if 'usuario' not in session or session.get('rol') != 'admin':
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        usuario = request.form['usuario'].upper()
        contrasena = request.form['contrasena']
        rol = request.form['rol']

        if Usuario.query.filter_by(usuario=usuario).first():
            flash('El usuario ya existe.', 'warning')
            return redirect(url_for('auth.registrar_usuario'))

        nuevo_usuario = Usuario(usuario=usuario, rol=rol)
        nuevo_usuario.set_password(contrasena)

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario registrado correctamente', 'success')
        return redirect(url_for('admin.panel'))

    return render_template('registrar_usuario.html')
