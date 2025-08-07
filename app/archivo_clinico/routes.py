# app/archivo_clinico/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request,jsonify,session
from app.models.archivo_clinico import ArchivoClinico,Paciente,SolicitudExpediente
from app.models.personal import Usuario,Servicio
from app.utils.helpers import login_required
from app import db
from datetime import datetime

bp = Blueprint('archivo_clinico', __name__, template_folder='templates/archivo_clinico')

@bp.route('/')
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def index():
    archivos = ArchivoClinico.query.all()
    return render_template('archivo_clinico/listar.html', archivos=archivos)

@bp.route('/alta', methods=['GET', 'POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def agregar_archivo():
    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
       
        if not id_paciente:
            flash("Debes seleccionar un paciente válido.", "danger")
            return redirect(request.url)

        nuevo = ArchivoClinico(
            id_paciente=id_paciente,
            ubicacion_fisica=request.form['ubicacion_fisica'],
            estado=request.form['estado'],
            tipo_archivo=request.form['tipo_archivo'],
            fecha_creacion=request.form['fecha_creacion']
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Archivo clínico guardado correctamente", "success")
        return redirect(url_for('archivo_clinico.index'))

    return render_template('archivo_clinico/agregar.html')

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def editar_archivo(id):
    archivo = ArchivoClinico.query.get_or_404(id)
    if request.method == 'POST':
        archivo.ubicacion_fisica = request.form['ubicacion_fisica']
        archivo.estado = request.form['estado']
        archivo.tipo_archivo = request.form['tipo_archivo']
        archivo.fecha_creacion = request.form['fecha_creacion']
        db.session.commit()
        flash('Archivo clínico actualizado.', 'success')
        return redirect(url_for('archivo_clinico.index'))
    return render_template('archivo_clinico/editar.html', archivo=archivo)

@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required(roles=['Administrador'])
def eliminar_archivo(id):
    archivo = ArchivoClinico.query.get_or_404(id)
    db.session.delete(archivo)
    db.session.commit()
    flash('Archivo eliminado correctamente.', 'success')
    return redirect(url_for('archivo_clinico.index'))
#===========================================================================================Solicitudes de Expedientes
@bp.route('/archivo/solicitudes')
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def lista_solicitudes():
    solicitudes = SolicitudExpediente.query.order_by(SolicitudExpediente.fecha_solicitud.desc()).all()
    return render_template('archivo_clinico/solicitudes.html', solicitudes=solicitudes)

@bp.route('/archivo/solicitudes/nueva', methods=['GET', 'POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def nueva_solicitud():
    pacientes = Paciente.query.all()
    usuarios = Usuario.query.all()
    servicios = Servicio.query.filter_by(area='Paciente').all()
    if request.method == 'POST':
        id_paciente = request.form['id_paciente']
        id_usuario_solicita = request.form['id_usuario_solicita']
        id_servicio=request.form['id_servicio']
       
        # Buscar el expediente relacionado al paciente
        expediente = ArchivoClinico.query.filter_by(id_paciente=id_paciente).first()

        if not expediente:
            flash('Este paciente no tiene expediente registrado.', 'danger')
            return redirect(request.url)
        
        # Verifica si el expediente ya tiene una solicitud activa SolicitudExpediente
        solicitud_activa = SolicitudExpediente.query.filter_by(id_archivo=expediente.id_archivo).filter(
            SolicitudExpediente.estado_solicitud.in_(['pendiente', 'entregado'])
        ).first()

        if solicitud_activa:
            flash("Este expediente ya tiene una solicitud activa (pendiente o entregado).", "warning")
            return redirect(url_for('archivo_clinico.nueva_solicitud'))

        nueva = SolicitudExpediente(
            id_paciente=id_paciente,
            id_archivo=expediente.id_archivo,
            id_usuario_solicita=id_usuario_solicita,
            fecha_solicitud=datetime.now(),
            estado_solicitud='pendiente',
            id_servicio=id_servicio
        )

        db.session.add(nueva)
        db.session.commit()
        flash('Solicitud guardada correctamente.', 'success')
        return redirect(url_for('archivo_clinico.lista_solicitudes'))

    return render_template('archivo_clinico/nueva_solicitud.html', pacientes=pacientes, usuarios=usuarios,servicios=servicios)


@bp.route('/archivo/solicitudes/<int:id>/entregar', methods=['POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def entregar_solicitud(id):
    solicitud = SolicitudExpediente.query.get_or_404(id)
    
    if solicitud.estado_solicitud != 'pendiente':
        flash("La solicitud no está en estado pendiente", "danger")
        return redirect(url_for('archivo_clinico.lista_solicitudes'))
    
    id_autoriza = session.get('usuario')
    if not id_autoriza:
        flash("No se detectó usuario en sesión para autorizar", "danger")
        return redirect(url_for('archivo_clinico.lista_solicitudes'))
    
    solicitud.estado_solicitud = 'entregado'
    solicitud.fecha_entrega = datetime.utcnow()
    solicitud.id_usuario_autoriza = session.get('usuario_id')  # ✅ cambio aquí
    
    # ✅ Confirmar que se guarda
    try:
        db.session.commit()
        flash("Expediente entregado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al guardar: {str(e)}", "danger")

    return redirect(url_for('archivo_clinico.lista_solicitudes'))

@bp.route('/archivo/solicitudes/<int:id>/devolver', methods=['POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def devolver_solicitud(id):
    solicitud = SolicitudExpediente.query.get_or_404(id)
    if solicitud.estado_solicitud != 'entregado':
        flash("Solo se pueden devolver expedientes ya entregados", "danger")
        return redirect(url_for('archivo_clinico.lista_solicitudes'))

    solicitud.estado_solicitud = 'devuelto'
    solicitud.fecha_devolucion = datetime.utcnow()
    db.session.commit()
    flash("Expediente devuelto correctamente", "success")
    return redirect(url_for('archivo_clinico.lista_solicitudes'))

