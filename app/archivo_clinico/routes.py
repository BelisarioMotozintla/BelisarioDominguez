# app/archivo_clinico/routes.py
from sqlite3 import IntegrityError
from flask import Blueprint, current_app, render_template, redirect, url_for, flash, request,jsonify,session,make_response
from app.models.archivo_clinico import ArchivoClinico,Paciente,SolicitudExpediente
from app.models.citas import Cita
from app.models.personal import Usuario,Servicio
from app.models.medicos import Consulta
from app.utils.helpers import roles_required
from app import db
from datetime import date, datetime
from sqlalchemy import func,cast, String,or_
from sqlalchemy.orm import joinedload, aliased
from weasyprint import HTML
from app.utils.helpers import usuarios_con_rol_requerido
from flask_login import current_user

bp = Blueprint('archivo_clinico', __name__, template_folder='templates/archivo_clinico')

@bp.route('/')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def index():
    query = request.args.get('q', '').strip()

    archivos_query = ArchivoClinico.query.options(
        joinedload(ArchivoClinico.paciente)
    )

    if query:
        archivos_query = archivos_query.join(Paciente).filter(
            (Paciente.nombre.ilike(f"%{query}%")) |
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{query}%"))
        )

    try:
        archivos = (
            archivos_query
            .order_by(ArchivoClinico.fecha_creacion.desc())
            .limit(10)
            .all()
        )
    except Exception as e:
        current_app.logger.error(f"Error archivos clínicos: {e}")
        archivos = []

    return render_template(
        'archivo_clinico/listar.html',
        archivos=archivos,
        query=query
    )

@bp.route('/buscar_json')
def buscar_archivo_json():
    query = request.args.get('q', '').strip()
    archivos = ArchivoClinico.query.options(joinedload(ArchivoClinico.paciente))

    if query:
        archivos = archivos.join(Paciente).filter(
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{query}%")) |
            (Paciente.nombre.ilike(f"%{query}%")) |
            (Paciente.curp.ilike(f"%{query}%"))
        )

    archivos = archivos.order_by(ArchivoClinico.fecha_creacion.desc()).limit(10).all()

    return jsonify([
        {
            'id_archivo': a.id_archivo,
            'numero_expediente': a.numero_expediente,
            'paciente': {
                'id_paciente': a.paciente.id_paciente,
                'nombre': a.paciente.nombre,
                'curp': a.paciente.curp
            }
        } for a in archivos
    ])
@bp.route('/buscar')
@usuarios_con_rol_requerido
def buscar_expedientes():
    query = request.args.get('q', '').strip().upper()
    filtro = request.args.get('filtro', 'todo')

    archivos_query = ArchivoClinico.query.options(
        joinedload(ArchivoClinico.paciente)
    ).join(Paciente)

    current_app.logger.info(f"DEBUG BUSCAR => filtro={filtro} | q='{query}'")

    if query:
        condiciones = []

        if filtro in ('todo', 'nombre'):
            condiciones.append(Paciente.nombre.ilike(f"%{query}%"))

        if filtro in ('todo', 'curp'):
            condiciones.append(Paciente.curp.ilike(f"%{query}%"))

        if filtro in ('todo', 'direccion'):
            condiciones.append(Paciente.direccion.ilike(f"%{query}%"))

        if filtro in ('todo', 'municipio'):
            condiciones.append(Paciente.municipio.ilike(f"%{query}%"))

        if filtro in ('todo', 'celular'):
            condiciones.append(Paciente.celular.ilike(f"%{query}%"))

        if filtro in ('todo', 'expediente'):
            condiciones.append(
                cast(ArchivoClinico.numero_expediente, String)
                .ilike(f"%{query}%")
            )

        archivos_query = archivos_query.filter(or_(*condiciones))

    # ✅ ORDENAR (SIEMPRE)
    archivos_query = archivos_query.order_by(
        ArchivoClinico.fecha_creacion.desc()
    )

    # ✅ LÍMITE SEGÚN SI HAY BÚSQUEDA
    if query:
        archivos = archivos_query.all()          # o .limit(100).all()
    else:
        archivos = archivos_query.limit(5).all()

    # ✅ RETURN SIEMPRE (FUERA DE IFs)
    return render_template(
        'archivo_clinico/buscar_global.html',
        archivos=archivos,
        query=query,
        filtro=filtro
    )

@bp.route('/alta', methods=['GET', 'POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def agregar_archivo():
    paciente_preseleccionado = None
    id_paciente_query = request.args.get('id_paciente', type=int)
    
    if id_paciente_query:
        paciente_preseleccionado = Paciente.query.get(id_paciente_query)

    if request.method == 'POST':
        # Tomar id de paciente: primero del formulario, si existe
        id_paciente = request.form.get('id_paciente')
        if not id_paciente and paciente_preseleccionado:
            id_paciente = paciente_preseleccionado.id_paciente

        if not id_paciente:
            flash("Debes seleccionar un paciente válido.", "danger")
            return redirect(request.url)

        # Número de expediente
        numero = request.form.get('numero_expediente', '').strip()
        if not numero.isdigit():
            flash("El número de expediente debe ser numérico.", "danger")
            return redirect(request.url)
        numero_int = int(numero)

        # Validar existencia de expediente
        id_actual = request.args.get('id', type=int)
        query = ArchivoClinico.query.filter(ArchivoClinico.numero_expediente == numero_int)
        if id_actual:
            query = query.filter(ArchivoClinico.id_archivo != id_actual)
        if query.first():
            flash("El número de expediente ya existe. Por favor, usa otro.", "danger")
            return redirect(request.url)

        # Validar si el paciente ya tiene un archivo
        paciente = paciente_preseleccionado or Paciente.query.get(id_paciente)
        nombre_paciente = paciente.nombre if paciente else f"ID {id_paciente}"

        archivo_existente = ArchivoClinico.query.filter_by(id_paciente=id_paciente).first()
        if archivo_existente:
            flash(f"El paciente {nombre_paciente} ya tiene un archivo clínico.", "danger")
            return redirect(request.url)

        # Obtener otros campos con valores por defecto si no existen
        ubicacion_fisica = request.form.get('ubicacion_fisica', '').strip() or "Sin ubicación"
        estado = request.form.get('estado', 'disponible')
        tipo_archivo = request.form.get('tipo_archivo', 'FISICO')
        fecha_creacion = request.form.get('fecha_creacion', date.today().strftime("%Y-%m-%d"))

        # Crear nuevo archivo
        nuevo = ArchivoClinico(
            id_paciente=id_paciente,
            numero_expediente=numero_int,
            ubicacion_fisica=ubicacion_fisica,
            estado=estado,
            tipo_archivo=tipo_archivo,
            fecha_creacion=fecha_creacion
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Archivo clínico guardado correctamente", "success")
        return redirect(url_for('archivo_clinico.index'))

    # GET: calcular siguiente número candidato
    max_numero = db.session.query(func.max(ArchivoClinico.numero_expediente)).scalar()
    siguiente_numero = (int(max_numero) + 1) if max_numero else 1

    return render_template(
        'archivo_clinico/agregar.html',
        candidato_numero=siguiente_numero,
        fecha_hoy=date.today().strftime("%Y-%m-%d"),
        paciente_preseleccionado=paciente_preseleccionado
    )

@bp.route("/ver_expediente/<int:id_paciente>")
@usuarios_con_rol_requerido
#@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def ver_expediente(id_paciente):
    paciente = Paciente.query.get_or_404(id_paciente)

    citas = Cita.query.filter_by(paciente_id=id_paciente)\
        .order_by(Cita.fecha_hora.desc()).all()

    archivo = ArchivoClinico.query.filter_by(
        id_paciente=id_paciente
    ).first()

    solicitudes = []
    if archivo:
        solicitudes = SolicitudExpediente.query.filter_by(
            id_archivo=archivo.id_archivo
        ).order_by(
            SolicitudExpediente.fecha_solicitud.desc()
        ).all()

    return render_template(
        "archivo_clinico/ver_expediente.html",
        paciente=paciente,
        citas=citas,
        archivo=archivo,
        solicitudes=solicitudes
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
    numero = request.args.get('numero', '').strip()
    if not numero.isdigit():
        return jsonify({'existe': False})
    numero_int = int(numero)
    existe = ArchivoClinico.query.filter_by(numero_expediente=numero_int).first() is not None
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
    ).filter(SolicitudExpediente.estado_solicitud.in_(['pendiente', 'entregado'])) \
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
    # Cerrar la consulta activa del paciente
    if solicitud.paciente:
        consulta = Consulta.query.filter_by(
            id_paciente=solicitud.paciente.id_paciente,
            estado='ABIERTA'
        ).first()
        if consulta:
            consulta.estado = 'CERRADO'

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
#=========================================================Paciente sin archivo clinico asociado===================================
@bp.route('/pacientes_sin_archivo', methods=['GET'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def reporte_pacientes_sin_archivo():
    q = request.args.get('q', '').strip()  # texto de búsqueda

    # Base: pacientes sin archivo clínico
    query = Paciente.query.outerjoin(ArchivoClinico).filter(ArchivoClinico.id_archivo == None)

    if q:
        # Filtrar por nombre o CURP
        query = query.filter(
            (Paciente.nombre.ilike(f"%{q}%")) |
            (Paciente.curp.ilike(f"%{q}%"))
        )

    pacientes_sin_archivo = query.all()
    return render_template('archivo_clinico/pacientes_sin_archivo.html', pacientes=pacientes_sin_archivo, q=q)

