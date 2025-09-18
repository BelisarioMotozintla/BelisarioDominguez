from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify,session
from app.models.archivo_clinico import Paciente,UnidadSalud,PacienteUnidad
from app.utils.helpers import roles_required
from app import db
from sqlalchemy import or_, cast, Date
from datetime import date
from datetime import datetime
from datetime import datetime, date



bp = Blueprint('paciente', __name__, template_folder='templates/paciente')

@bp.route('/')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_pacientes():
    query = request.args.get("q", "").strip()

    base_query = Paciente.query

    if query:
        base_query = base_query.filter(
            or_(
                Paciente.nombre.ilike(f"%{query}%"),
                Paciente.curp.ilike(f"%{query}%")
            )
        )

    pacientes = base_query.order_by(Paciente.id_paciente.desc()).limit(5).all()  # últimos 5

    return render_template(
        'paciente/listar.html',
        pacientes=pacientes,
        query=query
    )


@bp.route('/alta', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador', 'USUARIOMEDICO', 'UsuarioPasante'])
def alta_paciente():
    if request.method == 'POST':
        # Normalizar CURP
        curp = request.form.get('curp', '').strip().upper()

        # Verificar si el CURP ya existe
        existente = Paciente.query.filter_by(curp=curp).first()
        if existente:
            flash('Ya existe un paciente registrado con ese CURP.', 'danger')
            return redirect(url_for('paciente.alta_paciente'))

        # Validar fecha de nacimiento
        fecha_str = request.form.get('fecha_nacimiento')
        fecha_nac = None
        if fecha_str:
            try:
                fecha_nac = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                if fecha_nac < date(1900, 1, 1) or fecha_nac > date.today():
                    flash("La fecha de nacimiento no es válida.", "danger")
                    return redirect(url_for('paciente.alta_paciente'))
            except ValueError:
                flash("Formato de fecha incorrecto.", "danger")
                return redirect(url_for('paciente.alta_paciente'))

        # Cronicidad
        es_cronico = request.form.get('es_cronico') == 'Sí'
        tipo_cronicidad = request.form.get('tipo_cronicidad')

        if not es_cronico:
            tipo_cronicidad = "Otro"

        # Embarazo
        esta_embarazada = request.form.get('esta_embarazada') == 'Sí'

        # Planificación (checkbox o toggle que envía 'true'/'false')
        planificacion = request.form.get('planificacion') == 'true'

        # Reglas de exclusión
        if esta_embarazada:
            planificacion = False
        elif planificacion:
            esta_embarazada = False

        # Crear nuevo paciente
        nuevo = Paciente(
            nombre=request.form.get('nombre', '').strip(),
            curp=curp,
            fecha_nacimiento=fecha_nac,
            sexo=request.form.get('sexo'),
            direccion=request.form.get('direccion'),
            es_cronico=es_cronico,
            tipo_cronicidad=tipo_cronicidad,
            esta_embarazada=esta_embarazada,
            planificacion=planificacion
        )
        db.session.add(nuevo)
        db.session.flush()  # Obtener ID sin commit aún

        # Datos de unidad y tipo de relación
        id_unidad = request.form.get('id_unidad')
        tipo_relacion = request.form.get('tipo_relacion')
        fecha_relacion = date.today()

        relacion = PacienteUnidad(
            id_paciente=nuevo.id_paciente,
            id_unidad=id_unidad,
            tipo_relacion=tipo_relacion,
            fecha_relacion=fecha_relacion
        )
        db.session.add(relacion)
        db.session.commit()

        flash('Paciente registrado correctamente', 'success')

        rol = session.get('rol')
        if rol in ('USUARIOMEDICO', 'UsuarioPasante'):
            return redirect(url_for('medicos.menu_medico'))
        else:
            return redirect(url_for('paciente.listar_pacientes'))

    # GET: cargar unidades y fecha actual para el formulario
    unidades = UnidadSalud.query.order_by(UnidadSalud.nombre).all()
    hoy = date.today().isoformat()
   # aquí decides la URL de regreso
    rol = session.get('rol')
    if rol in ('USUARIOMEDICO', 'UsuarioPasante'):
        volver_url = url_for('medicos.menu_medico')
    else:
        volver_url = url_for('paciente.listar_pacientes')

    return render_template(
        'paciente/alta.html',
        unidades=unidades,
        hoy=hoy,
        paciente=None,
        volver_url=volver_url
    )

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def editar_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    relacion = PacienteUnidad.query.filter_by(id_paciente=paciente.id_paciente).first()
    unidades = UnidadSalud.query.order_by(UnidadSalud.nombre).all()

    if request.method == 'POST':

        # Manejo de cronicidad
        es_cronico = request.form.get('es_cronico') == 'Sí'
        tipo_cronicidad = request.form.get('tipo_cronicidad')
        if not es_cronico:
            tipo_cronicidad = "Otro"

        # Manejo de embarazo y planificación
        esta_embarazada = request.form.get('esta_embarazada') == 'Sí'
        planificacion = request.form.get('planificacion') == 'true'

        # Reglas de exclusión
        if esta_embarazada:
            planificacion = False
        elif planificacion:
            esta_embarazada = False

        # Datos del paciente
        paciente.nombre = request.form['nombre']
        paciente.curp = request.form['curp']

        # Parseo seguro de fecha
        fecha_nacimiento_str = request.form.get('fecha_nacimiento')
        if fecha_nacimiento_str:
            try:
                paciente.fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Formato de fecha inválido. Use AAAA-MM-DD.", "danger")

        paciente.sexo = request.form['sexo']
        paciente.direccion = request.form.get('direccion')
        paciente.es_cronico = es_cronico
        paciente.tipo_cronicidad = tipo_cronicidad
        paciente.esta_embarazada = esta_embarazada
        paciente.planificacion = planificacion
       
        # Datos de relación con la unidad
        id_unidad = request.form.get('id_unidad')
        tipo_relacion = request.form.get('tipo_relacion')

        if relacion:
            relacion.id_unidad = id_unidad
            relacion.tipo_relacion = tipo_relacion
        else:
            nueva_relacion = PacienteUnidad(
                id_paciente=paciente.id_paciente,
                id_unidad=id_unidad,
                tipo_relacion=tipo_relacion,
                fecha_relacion=date.today()
            )
            db.session.add(nueva_relacion)

        db.session.commit()
        flash('Paciente actualizado correctamente', 'success')
        return redirect(url_for('paciente.listar_pacientes'))

    return render_template(
        'paciente/editar.html',
        paciente=paciente,
        relacion=relacion,
        unidades=unidades
    )
@bp.route('/buscar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def buscar_paciente():
    query = request.args.get('query', '').strip()
    resultados = []
    if query:
        resultados = Paciente.query.filter(
            (Paciente.nombre.ilike(f'%{query}%')) |
            (Paciente.curp.ilike(f'%{query}%'))
        ).limit(10).all()

    return jsonify([
        {'id_paciente': p.id_paciente, 'nombre': p.nombre, 'curp': p.curp}
        for p in resultados
    ])

@bp.route('/eliminar/<int:id>', methods=['POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def eliminar_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    db.session.delete(paciente)
    db.session.commit()
    flash('Paciente eliminado correctamente.', 'success')
    return redirect(url_for('paciente.listar_pacientes'))

def digito_verificador(curp17, anio):
    """
    curp17: primeros 17 caracteres de la CURP
    anio: año de nacimiento (YYYY)
    """
    tabla = {
        '0':0, '1':1, '2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9,
        'A':10,'B':11,'C':12,'D':13,'E':14,'F':15,'G':16,'H':17,'I':18,'J':19,
        'K':20,'L':21,'M':22,'N':23,'Ñ':24,'O':25,'P':26,'Q':27,'R':28,'S':29,
        'T':30,'U':31,'V':32,'W':33,'X':34,'Y':35,'Z':36
    }

    contador = 18
    sumatoria = 0
    for c in curp17.upper():
        valor = tabla.get(c, 0)
        sumatoria += valor * contador
        contador -= 1

    numVer = (10 - (sumatoria % 10)) % 10

    if int(anio) < 2000:
        dig_ver = f"0{numVer}"
    else:
        dig_ver = f"A{numVer}"

    return dig_ver
@bp.route('/calcular_digito', methods=['POST'])
def calcular_digito():
    curp17 = request.json.get('curp17')  # primeros 17 caracteres
    anio = request.json.get('anio')      # año de nacimiento YYYY
    dig_ver = digito_verificador(curp17, anio)
    return jsonify({"digito": dig_ver})


@bp.route("/reporte_condicion", methods=["GET", "POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def reporte_condicion():
    filtros = request.args.getlist("filtro")  # devuelve lista de opciones seleccionadas
    query = Paciente.query

    condiciones = []

    for f in filtros:
        if f == "Hipertenso":
            condiciones.append(Paciente.tipo_cronicidad == "Hipertenso")
        elif f == "Diabético":
            condiciones.append(Paciente.tipo_cronicidad == "Diabético")
        elif f == "Metabólico":
            condiciones.append(Paciente.tipo_cronicidad == "Metabólico")
        elif f == "Embarazada":
            condiciones.append(Paciente.esta_embarazada == True)
        elif f == "Planificación":
            condiciones.append(Paciente.planificacion == True)

    if condiciones:
        pacientes = query.filter(or_(*condiciones)).all()  # filtra cualquiera de las condiciones
    else:
        pacientes = query.all()  # si no hay filtro, todos

    return render_template("paciente/reporte_condicion.html", pacientes=pacientes, filtro=filtros)
