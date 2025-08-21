from flask import Blueprint, render_template, request, redirect, url_for, flash, session,jsonify
from app.models.personal import Empleado, Usuario, Roles, Puesto, Turno, Servicio
from app.models.archivo_clinico import UnidadSalud
from app.utils.db import db
from werkzeug.security import generate_password_hash
from app.utils.helpers import roles_required
from . import personal_bp as bp


def obtener_id_usuario_actual():
    usuario = Usuario.query.filter_by(usuario=session.get('usuario')).first()
    return usuario.id_usuario if usuario else None

@bp.route('/')
@roles_required(['SuperUsuario', 'Administrador'])
def index():
    empleados = Empleado.query.all()
    return render_template('personal/lista_empleados.html', empleados=empleados)

@bp.route('/agregar', methods=['GET', 'POST'])
@roles_required(['SuperUsuario', 'Administrador'])
def agregar():
    roles = Roles.query.all()
    puestos = Puesto.query.all()
    turnos = Turno.query.all()
    unidadsalud = UnidadSalud.query.all()
    servicios = Servicio.query.all()

    # Usuarios que aún no están asignados a un empleado
    usuarios_disponibles = Usuario.query.filter(Usuario.id_empleado == None).all()
    usuario_asociado = None

    if request.method == 'POST':
        # Crear empleado
        empleado = Empleado(
	    tipo_trabajador=request.form['tipo_trabajador'],
            curp=request.form['curp'],
            rfc=request.form['rfc'],
            no_biometrico=request.form['no_biometrico'],
            nombre=request.form['nombre'],
            apellido_paterno=request.form['apellido_paterno'],
            apellido_materno=request.form['apellido_materno'],
            titulo=request.form['titulo'],
            cedula=request.form['cedula'],
            fecha_ingreso=request.form['fecha_ingreso'] or None,
            horario=request.form['horario'],
            dias_laborables=request.form['dias_laborables'],
            horas_laborales=request.form['horas_laborales'] or None,
            email=request.form['email'],
            telefono=request.form['telefono'],
            direccion=request.form['direccion'],
            id_puesto=request.form['id_puesto'],
            id_turno=request.form['id_turno'],
            id_unidad=request.form['id_unidad'],
            id_servicio=request.form['id_servicio']
        )
        db.session.add(empleado)
        db.session.flush()

        # Asociar usuario si se seleccionó uno
        usuario_id = request.form.get('usuario_id')
        if usuario_id:
            usuario = Usuario.query.get(usuario_id)
            usuario.id_empleado = empleado.id_empleado

        db.session.commit()
        flash('Empleado y usuario asociado correctamente.', 'success')
        return redirect(url_for('personal.index'))

    return render_template('personal/agregar_empleado.html',
                           roles=roles,
                           puestos=puestos,
                           turnos=turnos,
                           unidadsalud=unidadsalud,
                           servicios=servicios,
                           usuarios_disponibles=usuarios_disponibles,
                           usuario_asociado=usuario_asociado)

@bp.route('/editar/<int:id_empleado>', methods=['GET', 'POST'])
@roles_required(['SuperUsuario', 'Administrador'])
def editar(id_empleado):
    empleado = Empleado.query.get_or_404(id_empleado)
    usuario = Usuario.query.filter_by(id_empleado=id_empleado).first()
    roles = Roles.query.all()
    puestos = Puesto.query.all()
    turnos = Turno.query.all()
    unidadsalud = UnidadSalud.query.all()
    servicios = Servicio.query.all()

    if request.method == 'POST':
        # Actualizar campos del empleado
        empleado.tipo_trabajador = request.form['tipo_trabajador']
        empleado.curp = request.form['curp']
        empleado.rfc = request.form['rfc']
        empleado.no_biometrico = request.form['no_biometrico']
        empleado.nombre = request.form['nombre']
        empleado.apellido_paterno = request.form['apellido_paterno']
        empleado.apellido_materno = request.form['apellido_materno']
        empleado.titulo = request.form['titulo']
        empleado.cedula = request.form['cedula']
        empleado.fecha_ingreso = request.form['fecha_ingreso'] or None
        empleado.horario = request.form['horario']
        empleado.dias_laborables = request.form['dias_laborables']
        empleado.horas_laborales = request.form['horas_laborales'] or None
        empleado.email = request.form['email']
        empleado.telefono = request.form['telefono']
        empleado.direccion = request.form['direccion']
        empleado.id_puesto = request.form['id_puesto']
        empleado.id_turno = request.form['id_turno']
        empleado.id_unidad = request.form['id_unidad']
        empleado.id_servicio = request.form['id_servicio']

        # Actualizar campos del usuario asociado
        if usuario:
            usuario.usuario = request.form['usuario']
            usuario.id_rol = request.form['rol_id']
            nueva_contrasena = request.form.get('contrasena')
            if nueva_contrasena:
                usuario.contrasena_hash = generate_password_hash(nueva_contrasena)

        db.session.commit()
        flash('Empleado y usuario actualizados correctamente.', 'success')
        return redirect(url_for('personal.index'))

    return render_template('personal/editar_empleado.html',
                           empleado=empleado,
                           usuario=usuario,
                           roles=roles,
                           puestos=puestos,
                           turnos=turnos,
                           unidadsalud=unidadsalud,
                           servicios=servicios)

@bp.route('/eliminar/<int:id_empleado>', methods=['POST'])
@roles_required(['SuperUsuario', 'Administrador'])
def eliminar(id_empleado):
    empleado = Empleado.query.get_or_404(id_empleado)
    usuario = Usuario.query.filter_by(id_empleado=id_empleado).first()
    if usuario:
        db.session.delete(usuario)
    db.session.delete(empleado)
    db.session.commit()
    flash('Empleado y usuario eliminados correctamente.', 'success')
    return redirect(url_for('personal.index'))

@bp.route('/editar_empleado/<int:id_empleado>', methods=['GET', 'POST'])
@roles_required([ 'Administrador'])
def editar_empleado(id_empleado):
    empleado = Empleado.query.get_or_404(id_empleado)
    usuario = Usuario.query.filter_by(id_empleado=id_empleado).first()
    puestos = Puesto.query.all()
    turnos = Turno.query.all()
    unidadsalud = UnidadSalud.query.all()
    servicios = Servicio.query.all()
    roles = Roles.query.all()

    if request.method == 'POST':
        empleado.curp = request.form['curp']
        empleado.nombre = request.form['nombre']
        empleado.id_puesto = request.form['id_puesto']
        empleado.id_turno = request.form['id_turno']
        empleado.id_adscripcion = request.form['id_adscripcion']
        empleado.id_servicio = request.form['id_servicio']

        usuario.usuario = request.form['usuario']
        usuario.rol_id = request.form['rol_id']

        nueva_contra = request.form.get('contrasena')
        if nueva_contra:
            usuario.contrasena = generate_password_hash(nueva_contra).decode('utf-8')

        db.session.commit()
        flash('Empleado y usuario actualizados correctamente.', 'success')
        return redirect(url_for('personal.index'))

    return render_template('editar_empleado.html',
                           empleado=empleado,
                           usuario=usuario,
                           puestos=puestos,
                           turnos=turnos,
                           unidadsalud=unidadsalud,
                           servicios=servicios,
                           roles=roles)

