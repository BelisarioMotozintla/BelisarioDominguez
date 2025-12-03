from io import BytesIO
from flask import send_file
import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify,session
from app.models.archivo_clinico import Paciente,UnidadSalud,PacienteUnidad
from app.models.citas import Cita
from app.utils.helpers import roles_required
from app import db
from sqlalchemy import and_, extract, func, or_, cast, Date
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
@bp.route('/alta/<int:id_cita>', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador', 'USUARIOMEDICO', 'UsuarioPasante'])
def alta_paciente(id_cita=None):   # 👈 IMPORTANTE
    faltantes = []  # ✅ Inicializamos siempre
    # Captura id_cita de la URL: /alta?id_cita=10
    id_cita_arg = request.args.get('id_cita', type=int)

    # Elige el que exista: primero el de la query, luego el de la ruta
    id_cita = id_cita_arg if id_cita_arg is not None else id_cita

    cita = None

    if id_cita:
        cita = Cita.query.get(id_cita)
    
    #id_cita = request.args.get('id_cita', None, type=int)   # 🟢 CAPTURAR CITA SI VIENE DE ARCHIVO CLÍNICO
    
    
    #if id_cita:
     #   cita = Cita.query.get(id_cita)   # Busca la cita en la BD
    
   # cita = None

    if request.method == 'POST':
        # --- Obtener datos del formulario ---
        nombre = request.form.get('nombre', '').strip()
        curp = request.form.get('curp', '').strip().upper()
        sexo = request.form.get('sexo', '').strip()
        direccion = request.form.get('direccion', '').strip()
        municipio = request.form.get('municipio', '').strip()    # ← NUEVO
        celular = request.form.get('celular', '').strip()        # ← NUEVO
        id_unidad = request.form.get('id_unidad')
        tipo_relacion = request.form.get('tipo_relacion')

        # --- Validar campos vacíos ---
        campos_requeridos = {
            'Nombre': nombre,
            'CURP': curp,
            'Sexo': sexo,
            'Dirección': direccion,
            'Municipio': municipio,      # ← NUEVO
            'Celular': celular,          # ← NUEVO
            'Unidad de salud': id_unidad,
            'Tipo de relación': tipo_relacion
        }

        faltantes = [campo for campo, valor in campos_requeridos.items() if not valor]
        if faltantes:
            flash(f"Faltan los siguientes campos obligatorios: {', '.join(faltantes)}", "danger")
            return redirect(url_for('paciente.alta_paciente'))

        # --- Validar duplicado de CURP ---
        existente = Paciente.query.filter_by(curp=curp).first()
        if existente:
            flash('Ya existe un paciente registrado con ese CURP.', 'danger')
            return redirect(url_for('paciente.alta_paciente'))

        # --- Validar fecha de nacimiento ---
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

        # --- Campos de cronicidad ---
        es_cronico = request.form.get('es_cronico') == 'Sí'
        tipo_cronicidad = request.form.get('tipo_cronicidad') if es_cronico else "Otro"

        # --- Campos de embarazo y planificación ---
        esta_embarazada = request.form.get('esta_embarazada') == 'Sí'
        planificacion = request.form.get('planificacion') == 'true'

        # --- Reglas de exclusión ---
        if esta_embarazada:
            planificacion = False
        elif planificacion:
            esta_embarazada = False

        # --- Crear paciente ---
        nuevo = Paciente(
            nombre=nombre,
            curp=curp,
            fecha_nacimiento=fecha_nac,
            sexo=sexo,
            direccion=direccion,
            municipio=municipio,   # ← NUEVO
            celular=celular,       # ← NUEVO
            es_cronico=es_cronico,
            tipo_cronicidad=tipo_cronicidad,
            esta_embarazada=esta_embarazada,
            planificacion=planificacion
        )
        db.session.add(nuevo)
        db.session.flush()  # Obtener ID sin commit aún

        # --- Registrar relación con unidad ---
        relacion = PacienteUnidad(
            id_paciente=nuevo.id_paciente,
            id_unidad=id_unidad,
            tipo_relacion=tipo_relacion,
            fecha_relacion=date.today()
        )
        db.session.add(relacion)
        db.session.commit()
        # 🟢 SI EL REGISTRO VIENE DE UNA CITA → ASOCIAR AUTOMÁTICAMENTE
        if id_cita:
            cita = Cita.query.get(id_cita)
            if cita:
                cita.paciente_id = nuevo.id_paciente
                db.session.commit()
                flash("Paciente registrado y asociado a la cita correctamente.", "success")
                return redirect(url_for('archivo_clinico.citas_dia'))

        db.session.commit()
        flash('Paciente registrado correctamente.', 'success')

        rol = session.get('rol')
        if rol in ('USUARIOMEDICO', 'UsuarioPasante'):
            return redirect(url_for('medicos.menu_medico'))
        else:
            return redirect(url_for('paciente.listar_pacientes'))

    # --- Si no es POST o hay validaciones pendientes ---
    rol = session.get('rol')
    volver_url = (
        url_for('medicos.menu_medico')
        if rol in ('USUARIOMEDICO', 'UsuarioPasante')
        else url_for('paciente.listar_pacientes')
    )
    unidades = UnidadSalud.query.order_by(UnidadSalud.nombre).all()
    hoy = date.today().isoformat()

    # Siempre retornar la vista
    return render_template(
        'paciente/alta.html',
        unidades=unidades,
        hoy=hoy,
        paciente=None,
        volver_url=volver_url,
        id_cita=id_cita,
        cita=cita,
        faltantes=faltantes
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

        # 🔹 Datos del paciente
        paciente.nombre = request.form['nombre']
        paciente.curp = request.form['curp']

        # Fecha segura
        fecha_nacimiento_str = request.form.get('fecha_nacimiento')
        if fecha_nacimiento_str:
            try:
                paciente.fecha_nacimiento = datetime.strptime(fecha_nacimiento_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Formato de fecha inválido. Use AAAA-MM-DD.", "danger")

        paciente.sexo = request.form['sexo']
        paciente.direccion = request.form.get('direccion')

        # 🔥 Nuevos campos
        paciente.municipio = request.form.get('municipio')
        paciente.celular = request.form.get('celular')

        paciente.es_cronico = es_cronico
        paciente.tipo_cronicidad = tipo_cronicidad
        paciente.esta_embarazada = esta_embarazada
        paciente.planificacion = planificacion

        # 🔹 Relación Paciente–Unidad
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
    universo_trabajo = request.args.get("universo_trabajo")  # checkbox
    query = Paciente.query
    descargar = request.args.get("descargar")

    condiciones = []
    pacientes = []

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
        elif f == "MujeresEdadReproductiva":
                condiciones.append(
                    and_(
                        Paciente.sexo == "F",
                        extract('year', func.age(Paciente.fecha_nacimiento)) >= 15,
                        extract('year', func.age(Paciente.fecha_nacimiento)) <= 49
                    )
                )

     # --- Base query ---
    query = db.session.query(Paciente)

    # --- Si se marcó el check "Universo de trabajo", aplicar join y filtro ---
    if universo_trabajo:
        query = query.join(PacienteUnidad).filter(PacienteUnidad.tipo_relacion == "Universo")

    # --- Aplicar condiciones adicionales ---
    if condiciones:
        pacientes = query.filter(or_(*condiciones)).all()
    else:
        pacientes = query.all()
    
     # --- Si el usuario pidió DESCARGAR ---
    if descargar:
        data = [
            {
                "Nombre": f"{p.nombre} ",
                "Edad": p.edad,
                "Sexo": p.sexo,
                "Tipo Cronicidad": p.tipo_cronicidad or "",
                "Embarazada": "Sí" if p.esta_embarazada else "No",
                "Planificación": "Sí" if p.planificacion else "No",
                "Dirección":  p.direccion,
            }
            for p in pacientes
        ]

        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            download_name="reporte_condicion.xlsx",
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    return render_template(
        "paciente/reporte_condicion.html",
        pacientes=pacientes,
        filtro=filtros,
        universo_trabajo=universo_trabajo,
    )