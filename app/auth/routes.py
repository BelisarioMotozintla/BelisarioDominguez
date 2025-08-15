from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.utils.db import db
from app.models.personal import Usuario, Roles
from . import auth_bp as bp
#from werkzeug.security import check_password_hash
from flask_login import login_user


@bp.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip().upper()
        contrasena = request.form['contrasena']
        user = Usuario.query.filter_by(usuario=usuario).first()

        if user and user.check_password(contrasena):
            if user.rol is None:
                flash("Este usuario no tiene un rol asignado", "danger")
                return redirect(url_for('auth.login'))

            session['usuario'] = user.usuario
            session['rol'] = user.rol.nombre_rol
            flash('Inicio de sesión exitoso', 'success')

            rol = user.rol.nombre_rol
            next_page = request.args.get('next')
            login_user(user)
            print("Ruta next_page recibida:", next_page)

            rutas_seguras = {
                'enfermeria.formulario': 'enfermeria.formulario',
                'archivo_clinico.index': 'archivo_clinico.index'
            }

            if rol == 'UsuarioAdministrativo':
                if next_page in rutas_seguras:
                    return redirect(url_for(rutas_seguras[next_page]))
                else:
                    return redirect(url_for('archivo_clinico.index'))

            rol_rutas = {
                'Administrador': 'admin.panel',
                'UsuarioEnfermeria': 'enfermeria.formulario',
                'UsuarioAdmin': 'personal.index',
                'SuperUsuario': 'formatos.formatos',
                'USUARIOMEDICO': 'medicos.listar_notas'

            }

            ruta = rol_rutas.get(rol)
            if ruta:
                return redirect(url_for(ruta))

            flash('No tienes permiso para acceder', 'warning')
            return redirect(url_for('auth.login'))

        flash('Credenciales incorrectas', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('auth/login.html')



@bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('auth.login'))


