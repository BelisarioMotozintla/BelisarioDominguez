# app/archivo_clinico/routes.py
from sqlite3 import IntegrityError
from flask import Blueprint, render_template, redirect, url_for, flash, request,jsonify,session,make_response
from app.models.archivo_clinico import ArchivoClinico,Paciente,SolicitudExpediente
from app.models.personal import Usuario,Servicio
from app.utils.helpers import roles_required
from app import db
from datetime import date, datetime
from sqlalchemy import func,cast, String,or_
from sqlalchemy.orm import joinedload, aliased
from weasyprint import HTML
from flask_login import current_user

bp = Blueprint('archivo_clinico', __name__, template_folder='templates/archivo_clinico')

@bp.route('/')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def index():
    # Obtener término de búsqueda
    query = request.args.get('q', '').strip()

    archivos = ArchivoClinico.query.options(joinedload(ArchivoClinico.paciente))

    if query:
        archivos = archivos.join(Paciente).filter(
            (Paciente.nombre.ilike(f"%{query}%")) |
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{query}%"))
        )

    archivos = archivos.order_by(ArchivoClinico.fecha_creacion.desc()).limit(10).all()  # limitar a 50 registros

    return render_template('archivo_clinico/listar.html', archivos=archivos, query=query)
@bp.route('/alta', methods=['GET', 'POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def agregar_archivo():
    if request.method == 'POST':
        id_paciente = request.form.get('id_paciente')
        numero = request.form.get('numero_expediente', '').strip()

        existe = ArchivoClinico.query.filter_by(numero_expediente=numero).first()
        if existe:
            flash('El número de expediente ya existe. Por favor, usa otro.', 'danger')
            return redirect(request.url)
        else:
            if not id_paciente:
                flash("Debes seleccionar un paciente válido.", "danger")
                return redirect(request.url)

            nuevo = ArchivoClinico(
                id_paciente=id_paciente,
                ubicacion_fisica=request.form['ubicacion_fisica'],
                estado=request.form['estado'],
                tipo_archivo=request.form['tipo_archivo'],
                fecha_creacion=request.form['fecha_creacion'],
                numero_expediente=numero
            )
            db.session.add(nuevo)
            db.session.commit()
            flash("Archivo clínico guardado correctamente", "success")
            return redirect(url_for('archivo_clinico.index'))
    
    # Calcular siguiente número candidato
    max_numero = db.session.query(func.max(ArchivoClinico.numero_expediente)).scalar()
    siguiente_numero = (int(max_numero) + 1) if max_numero else 1

    return render_template(
        'archivo_clinico/agregar.html',
        candidato_numero=siguiente_numero,fecha_hoy=date.today().strftime("%Y-%m-%d")  # <-- pasar fecha al template
    )


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def editar_archivo(id):
    archivo = ArchivoClinico.query.get_or_404(id)

    if request.method == 'POST':
        nuevo_numero = request.form['numero_expediente'].strip()

        # Validar que no exista otro expediente con ese número
        existe = ArchivoClinico.query.filter(
            ArchivoClinico.numero_expediente == nuevo_numero,
            ArchivoClinico.id_archivo != id
        ).first()

        if existe:
            flash('El número de expediente ya existe, por favor elige otro.', 'danger')
            return render_template('archivo_clinico/editar.html', archivo=archivo)

        # Actualizar campos
        archivo.numero_expediente = nuevo_numero
        archivo.ubicacion_fisica = request.form['ubicacion_fisica']
        archivo.estado = request.form['estado']
        archivo.tipo_archivo = request.form['tipo_archivo']
        archivo.fecha_creacion = request.form['fecha_creacion']

        try:
            db.session.commit()
            flash('Archivo clínico actualizado.', 'success')
            return redirect(url_for('archivo_clinico.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Error al actualizar el archivo clínico.', 'danger')
            return render_template('archivo_clinico/editar.html', archivo=archivo)

    return render_template('archivo_clinico/editar.html', archivo=archivo)

@bp.route('/editarvalidar_numero_expediente_edit')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def validar_numero_expediente_edit():
    numero = request.args.get('numero', '').strip()
    id_actual = request.args.get('id', type=int)
    existe = False
    if numero:
        existe = ArchivoClinico.query.filter(
            ArchivoClinico.numero_expediente == numero,
            ArchivoClinico.id_archivo != id_actual
        ).first() is not None
    return jsonify({'existe': existe})


@bp.route('/eliminar/<int:id>', methods=['POST'])
@roles_required([ 'Administrador'])
def eliminar_archivo(id):
    archivo = ArchivoClinico.query.get_or_404(id)
    db.session.delete(archivo)
    db.session.commit()
    flash('Archivo eliminado correctamente.', 'success')
    return redirect(url_for('archivo_clinico.index'))

@bp.route('/validar_numero_expediente')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def validar_numero_expediente():
    numero = request.args.get('numero', '').strip()  # Valor por defecto '' si no existe
    existe = False
    if numero:
        existe = ArchivoClinico.query.filter_by(numero_expediente=numero).first() is not None
    return jsonify({'existe': existe})
#===========================================================================================Solicitudes de Expedientes
@bp.route('/archivo/solicitudes')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def lista_solicitudes():
    search = request.args.get('search', '').strip()
    
    # Query base con joins y solo solicitudes pendientes
    query = SolicitudExpediente.query.options(
        joinedload(SolicitudExpediente.paciente),
        joinedload(SolicitudExpediente.archivo),
        joinedload(SolicitudExpediente.usuario_solicita),
        joinedload(SolicitudExpediente.usuario_autoriza)
    ).filter(SolicitudExpediente.estado_solicitud == 'pendiente') \
     .order_by(SolicitudExpediente.fecha_solicitud.desc())

    if search:
        # Buscar por nombre de paciente, CURP o número de expediente
        query = query.join(Paciente) \
                     .join(ArchivoClinico, SolicitudExpediente.id_archivo == ArchivoClinico.id_archivo) \
                     .filter(
                         or_(
                             Paciente.nombre.ilike(f"%{search}%"),
                             Paciente.curp.ilike(f"%{search}%"),
                             cast(ArchivoClinico.numero_expediente, String).ilike(f"%{search}%")
                         )
                     )

    solicitudes = query.limit(50).all()  # Limitar resultados
    return render_template('archivo_clinico/solicitudes.html', solicitudes=solicitudes, search=search)


@bp.route('/archivo/solicitudes/nueva', methods=['GET', 'POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def nueva_solicitud():
    pacientes = Paciente.query.all()
    usuarios = Usuario.query.all()   # para llenar el select de "solicitante"
    servicios = Servicio.query.filter_by(area='Paciente').all()

    if request.method == 'POST':
        id_paciente = int(request.form['id_paciente'])
        id_usuario_solicita = int(request.form['id_usuario_solicita'])  # seleccionado en el form
        id_servicio = int(request.form['id_servicio'])
        id_usuario_autoriza = current_user.id_usuario  # el usuario logueado autoriza

        # Buscar el expediente relacionado al paciente
        expediente = ArchivoClinico.query.filter_by(id_paciente=id_paciente).first()
        if not expediente:
            flash('Este paciente no tiene expediente registrado.', 'danger')
            return redirect(request.url)

        # Verificar si ya hay una solicitud activa
        solicitud_activa = SolicitudExpediente.query.filter_by(
            id_archivo=expediente.id_archivo
        ).filter(
            SolicitudExpediente.estado_solicitud.in_(['pendiente', 'entregado'])
        ).first()

        if solicitud_activa:
            flash("Este expediente ya tiene una solicitud activa (pendiente o entregado).", "warning")
            return redirect(url_for('archivo_clinico.nueva_solicitud'))

        nueva = SolicitudExpediente(
            id_paciente=id_paciente,
            id_archivo=expediente.id_archivo,
            id_usuario_solicita=id_usuario_solicita,   # quien pide
            id_usuario_autoriza=id_usuario_autoriza,   # quien autoriza (logueado)
            fecha_solicitud=datetime.now(),
            estado_solicitud='pendiente',
            id_servicio=id_servicio
        )

        try:
            db.session.add(nueva)
            db.session.commit()
            flash('Solicitud guardada correctamente.', 'success')
            return redirect(url_for('archivo_clinico.lista_solicitudes'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error al guardar la solicitud: {e}", 'danger')
            return redirect(request.url)

    return render_template(
        'archivo_clinico/nueva_solicitud.html',
        pacientes=pacientes,
        usuarios=usuarios,   # sigue yendo al template para el select de solicitantes
        servicios=servicios
    )

@bp.route('/archivo/solicitudes/<int:id>/entregar', methods=['POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def entregar_solicitud(id):
    solicitud = SolicitudExpediente.query.get_or_404(id)
    id_usuario_autoriza = current_user.id_usuario  # el usuario logueado autoriza
    if solicitud.estado_solicitud != 'pendiente':
        flash("La solicitud no está en estado pendiente", "danger")
        return redirect(url_for('archivo_clinico.lista_solicitudes'))
    
   # id_autoriza = session.get('usuario')
    if not id_usuario_autoriza:
        flash("No se detectó usuario en sesión para autorizar", "danger")
        return redirect(url_for('archivo_clinico.lista_solicitudes'))
    
    solicitud.estado_solicitud = 'entregado'
    solicitud.fecha_entrega = datetime.utcnow()
    solicitud.id_usuario_autoriza = id_usuario_autoriza  # ✅ cambio aquí
    
    # ✅ Confirmar que se guarda
    try:
        db.session.commit()
        flash("Expediente entregado correctamente", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al guardar: {str(e)}", "danger")

    return redirect(url_for('archivo_clinico.lista_solicitudes'))

@bp.route('/archivo/solicitudes/<int:id>/devolver', methods=['POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
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

@bp.route('/cancelar_solicitud/<int:id>', methods=['POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def cancelar_solicitud(id):
    solicitud = SolicitudExpediente.query.get_or_404(id)
    solicitud.estado_solicitud = 'cancelado'
    db.session.commit()
    flash('Solicitud cancelada correctamente', 'info')
    return redirect(url_for('archivo_clinico.lista_solicitudes'))

@bp.route('/archivo/bitacora/pdf')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def imprimir_bitacora_pdf():
    # Obtener rango de fechas desde query string
    fecha_inicio_str = request.args.get('fecha_inicio')
    fecha_fin_str = request.args.get('fecha_fin')

    try:
        fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else date.today()
    except ValueError:
        fecha_inicio = date.today()

    try:
        fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else date.today()
    except ValueError:
        fecha_fin = date.today()

    # Alias de usuarios
    UsuarioSolicita = aliased(Usuario)
    UsuarioAutoriza = aliased(Usuario)

    # Consulta de registros dentro del rango
    registros = db.session.query(SolicitudExpediente)\
        .join(Paciente, Paciente.id_paciente == SolicitudExpediente.id_paciente)\
        .join(ArchivoClinico, ArchivoClinico.id_archivo == SolicitudExpediente.id_archivo)\
        .outerjoin(UsuarioSolicita, UsuarioSolicita.id_usuario == SolicitudExpediente.id_usuario_solicita)\
        .outerjoin(UsuarioAutoriza, UsuarioAutoriza.id_usuario == SolicitudExpediente.id_usuario_autoriza)\
        .filter(func.date(SolicitudExpediente.fecha_solicitud).between(fecha_inicio, fecha_fin))\
        .order_by(SolicitudExpediente.fecha_solicitud)\
        .all()

    # Renderizar plantilla HTML con rango
    html = render_template(
        'archivo_clinico/bitacora_pdf.html',
        registros=registros,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )

    # Generar PDF con WeasyPrint
    pdf = HTML(string=html).write_pdf()

    # Respuesta HTTP con el PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=bitacora_{fecha_inicio}_a_{fecha_fin}.pdf'

    return response