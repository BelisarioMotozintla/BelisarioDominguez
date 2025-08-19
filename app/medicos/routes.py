import textwrap
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file,jsonify, abort, current_app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, desc
from app.models.archivo_clinico import ArchivoClinico,Paciente,SolicitudExpediente
from app.models.personal import Usuario,Servicio
from app.utils.helpers import roles_required
from flask_login import current_user
from app.models.medicos import NotaConsultaExterna
from app import db
from app.medicos.forms import NotaConsultaForm
from datetime import datetime
from datetime import date
import io
import os
# Para generar PDF con WeasyPrint:
from weasyprint import HTML
from app.utils.validaciones_nota import campos_validos_nota_medica, get_float, get_str, get_date, get_time,calcular_imc

    
 

bp = Blueprint('medicos', __name__, template_folder='templates/medicos')


@bp.route('/')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def listar_notas():
    id_paciente = request.args.get('id_paciente', type=int)
    query = request.args.get('query', default='')

    notas = NotaConsultaExterna.query.order_by(NotaConsultaExterna.fecha.desc())

    if id_paciente:
        notas = notas.filter_by(id_paciente=id_paciente)

    notas = notas.all()

    for nota in notas:
        if nota.paciente and nota.paciente.fecha_nacimiento:
            nota.edad = (date.today() - nota.paciente.fecha_nacimiento).days // 365
        else:
            nota.edad = None

    return render_template('medicos/index.html',
                           notas=notas,
                           id_paciente=id_paciente,
                           query=query)


@bp.route('/nueva_nota/<int:id_paciente>', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def nueva_nota(id_paciente):
    paciente = Paciente.query.get_or_404(id_paciente)
    expediente = ArchivoClinico.query.filter_by(id_paciente=id_paciente).first()

    form = NotaConsultaForm()
    form.id_paciente.data = paciente.id_paciente
    if expediente:
        form.id_expediente.data = expediente.id_archivo

    if form.validate_on_submit():
        # Campos numéricos que aceptan cero si el usuario lo coloca
        def get_val(field):
            val = form.data.get(field)
            return float(val) if val not in [None, ''] else None

        peso = get_val('peso') or 0
        talla = get_val('talla') or 0
        imc = calcular_imc(peso, talla) if peso and talla else 0

        ta = form.ta.data.strip() or "0"
        fc = int(form.fc.data or 0)
        fr = int(form.fr.data or 0)
        temp = float(form.temp.data or 0)
        spo2 = int(form.spo2.data or 0)
        glicemia = int(form.glicemia.data or 0)

        # Crear nota
        nota = NotaConsultaExterna(
            id_paciente=paciente.id_paciente,
            id_expediente=expediente.id_archivo if expediente else None,
            id_usuario=current_user.id_usuario,
            fecha=form.fecha.data,
            hora=form.hora.data,
            peso=peso,
            talla=talla,
            imc=imc,
            ta=ta,
            fc=fc,
            fr=fr,
            temp=temp,
            spo2=spo2,
            glicemia=glicemia,
            cc=form.cc.data.strip() or "",
            antecedentes=form.antecedentes.data.strip() or "",
            exploracion_fisica=form.exploracion_fisica.data.strip() or "",
            diagnostico=form.diagnostico.data.strip() or "",
            plan=form.plan.data.strip() or "",
            pronostico=form.pronostico.data.strip() or "",
            laboratorio=form.laboratorio.data.strip() or "",
        )
        db.session.add(nota)
        db.session.commit()
        flash('Nota registrada correctamente', 'success')
        return redirect(url_for('medicos.ver_nota', id_nota=nota.id_nota))

    # Mostrar errores si hay POST inválido
    if request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", 'danger')

    if request.method == 'GET' and not form.fecha.data:
        from datetime import datetime
        form.fecha.data = datetime.utcnow().date()

    return render_template(
        'medicos/nueva_nota.html',
        form=form,
        paciente=paciente,
        expediente=expediente
    )

@bp.route('/editar/<int:id_nota>', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def editar_nota(id_nota):
    # Obtener la nota
    nota = NotaConsultaExterna.query.get_or_404(id_nota)

    # Obtener paciente y expediente relacionados
    paciente = nota.paciente
    expediente = ArchivoClinico.query.get(nota.id_expediente) if nota.id_expediente else None

    # Inicializar formulario con datos existentes
    form = NotaConsultaForm(obj=nota)

    # Choices (si realmente los necesitas en este formulario)
    form.id_paciente.choices = [(p.id_paciente, f"{p.nombre} {p.curp}") for p in Paciente.query.order_by(Paciente.nombre).all()]
    expedientes = ArchivoClinico.query.all()
    form.id_expediente.choices = [(e.id_archivo, f"{e.id_archivo} - {e.ubicacion_fisica[:40]}") for e in expedientes]
    form.id_expediente.choices.insert(0, (0, ' -- Ninguno -- '))

    if form.validate_on_submit():
        # Validar con la función reutilizable
        datos = form.data
        errores, datos_validados = campos_validos_nota_medica(datos)

        if errores:
            for e in errores:
                flash(e, "danger")
        else:
            # Guardar cambios
            nota.id_paciente = form.id_paciente.data
            id_expediente = form.id_expediente.data or None
            nota.id_expediente = id_expediente if id_expediente != 0 else None

            nota.fecha = datos_validados['fecha']
            nota.hora = form.hora.data
            nota.peso = datos_validados['peso']
            nota.talla = datos_validados['talla']
            nota.imc = calcular_imc(nota.peso, nota.talla)
            nota.ta = datos_validados['ta']
            nota.fc = datos_validados['fc']
            nota.fr = datos_validados['fr']
            nota.temp = datos_validados['temp']
            nota.spo2 = datos_validados['spo2']
            nota.glicemia = datos_validados['glicemia']
            nota.cc = form.cc.data.strip()

            # Texto largo
            nota.antecedentes = datos_validados['antecedentes']
            nota.exploracion_fisica = datos_validados['exploracion_fisica']
            nota.diagnostico = datos_validados['diagnostico']
            nota.plan = datos_validados['plan']
            nota.pronostico = datos_validados['pronostico']
            nota.laboratorio = datos_validados['laboratorio']

            db.session.commit()
            flash("Nota actualizada correctamente", "success")
            return redirect(url_for("medicos.ver_nota", id_nota=nota.id_nota))

    # Prellenar en GET
    if request.method == 'GET':
        form.id_paciente.data = nota.id_paciente
        form.id_expediente.data = nota.id_expediente or 0

        if not form.fecha.data:
            form.fecha.data = nota.fecha or datetime.utcnow().date()

    return render_template(
        "medicos/editar_nota.html",
        form=form,
        paciente=paciente,
        expediente=expediente,
        nota=nota
    )


#@bp.route("/medicos/ver_nota/<int:id_nota>")
@bp.route("/ver_nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador'])
def ver_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    paciente = nota.paciente
    medico = nota.usuario
    return render_template(
        'medicos/ver_nota.html',
        nota=nota,
        paciente=paciente,
        medico=medico,
        volver_url=request.referrer or url_for('medicos.listar_notas')
    )

@bp.route('/pdf/<int:id_nota>/pdf')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def nota_pdf(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    html = render_template('medicos/nota_pdf.html', nota=nota)
    # Generar PDF con WeasyPrint
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf),
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'nota_{nota.id_nota}.pdf')
""
@bp.route('/buscar_paciente')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def buscar_paciente():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    resultados = Paciente.query.join(Paciente.archivo_clinico)\
        .filter(
            (Paciente.nombre.ilike(f'%{query}%')) |
            (Paciente.curp.ilike(f'%{query}%'))
        ).limit(10).all()

    pacientes = []
    for p in resultados:
        expediente_id = p.archivo_clinico[0].id_archivo if p.archivo_clinico else None
        pacientes.append({
            'id_paciente': p.id_paciente,
            'nombre': p.nombre,
            'curp': p.curp,
            'id_expediente': expediente_id
        })

    return jsonify(pacientes)

@bp.route('/notas_paciente/<int:id_paciente>')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def notas_paciente(id_paciente):
    notas = (NotaConsultaExterna.query
             .filter_by(id_paciente=id_paciente)
             .order_by(NotaConsultaExterna.fecha.desc())
             .all())

    data = []
    for n in notas:
        edad = None
        if n.paciente and n.paciente.fecha_nacimiento:
            edad = (date.today() - n.paciente.fecha_nacimiento).days // 365

        # Médico: Nota → Usuario → Empleado
        nombre_medico = "Sin asignar"
        if n.usuario and n.usuario.empleado:
            nombre_medico = f"{n.usuario.empleado.nombre} {n.usuario.empleado.apellido_paterno} {n.usuario.empleado.apellido_materno}"

        data.append({
            "id_nota": n.id_nota,  # 👈 Esto es clave para el botón "Ver Nota"
            "fecha": n.fecha.strftime("%d/%m/%Y") if n.fecha else "",
            "medico": nombre_medico,
            "contenido": getattr(n, "contenido", getattr(n, "nota", "")),
            "edad": edad,
            "sexo": n.paciente.sexo if n.paciente else "",
            "curp": n.paciente.curp if n.paciente else ""
        })
    
    return jsonify(data)
@bp.route('/eliminar_nota/<int:id_nota>', methods=['POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def eliminar_nota(id_nota):
    # Buscar la nota
    nota = NotaConsultaExterna.query.get_or_404(id_nota)

    try:
        db.session.delete(nota)
        db.session.commit()
        flash('Nota eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la nota: {str(e)}', 'danger')

    # Redirigir a la lista de notas del paciente
    id_paciente = nota.id_paciente
    return redirect(url_for('medicos.listar_notas', id_paciente=id_paciente))


@bp.route('/buscarpaciente')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def buscarpaciente():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    pacientes = Paciente.query.filter(
        or_(
            Paciente.nombre.ilike(f'%{query}%'),
            Paciente.curp.ilike(f'%{query}%')
        )
    ).all()

    data = []
    for p in pacientes:
        # Obtener la última nota para mostrar nombre de médico en notas (si quieres)
        ultima_nota = NotaConsultaExterna.query.filter_by(id_paciente=p.id_paciente)\
                        .order_by(desc(NotaConsultaExterna.fecha)).first()

        nombre_medico = ""
        if ultima_nota:
            usuario = Usuario.query.get(ultima_nota.id_usuario)
            if usuario and usuario.empleado:
                nombre_medico = usuario.empleado.nombre

        data.append({
            "id_paciente": p.id_paciente,
            "nombre": p.nombre,
            "curp": p.curp,
            "medico": nombre_medico  # opcional, tu script no lo usa ahora
        })

    return jsonify(data)

def _plantilla_path():
    return os.path.join(current_app.root_path, "static", "medicos", "plantilla_nota.pdf")

def _build_coords():
    return {
        "nombre_paciente": (150, 655),
        "curp": (250, 638),
        "fecha_nacimiento": (500, 638),
        "direccion": (100, 625),
        "sexo": (550, 655),
        "edad": (440, 655),
        "expediente": (150, 638),
        "fecha": (80, 590),
        "hora": (85, 570),
        "peso": (85, 550),
        "talla": (85, 530),
        "ta": (85, 515),
        "fc": (85, 495),
        "fr": (85, 480),
        "temp": (85, 460),
        "cc": (85, 445),
        "spo2": (85, 430),
        "glicemia": (85, 410),
        "imc": (85, 390),
        "medico": (400, 45),
        "cedula": (400, 40),
    }

def ajustar_lineas(texto, max_caracteres):
    if not texto:
        return []
    return textwrap.wrap(texto, max_caracteres)


@bp.route("/nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador'])
def generar_nota_pdf(id_nota: int):
    debug = request.args.get("debug", "0") == "1"
    download = request.args.get("dl", "1") != "0"  # dl=0 => mostrar inline

    # -------- Registrar fuentes Montserrat --------
    font_dir = os.path.join(current_app.root_path, "static", "fonts")
    montserrat_regular = os.path.join(font_dir, "Montserrat-Regular.ttf")
    montserrat_bold = os.path.join(font_dir, "Montserrat-Bold.ttf")

    if not os.path.exists(montserrat_regular) or not os.path.exists(montserrat_bold):
        abort(500, description="No se encontraron los archivos de fuente Montserrat en static/fonts")

    pdfmetrics.registerFont(TTFont("Montserrat", montserrat_regular))
    pdfmetrics.registerFont(TTFont("Montserrat-Bold", montserrat_bold))

    # -------- 1) Consulta con joins --------
    nota = (
        db.session.query(NotaConsultaExterna)
        .options(
            joinedload(NotaConsultaExterna.paciente).joinedload(Paciente.archivo_clinico),
            joinedload(NotaConsultaExterna.usuario).joinedload(Usuario.empleado),
        )
        .filter(NotaConsultaExterna.id_nota == id_nota)
        .first()
    )

    if not nota:
        abort(404, description="Nota no encontrada")

    paciente = nota.paciente
    archivo = paciente.archivo_clinico[0] if paciente.archivo_clinico else None
    usuario_medico = nota.usuario
    medico_emp = usuario_medico.empleado if usuario_medico else None

    if paciente is None or archivo is None:
        abort(400, description="El paciente no tiene expediente asociado")
    if usuario_medico is None or medico_emp is None:
        abort(400, description="La nota no tiene médico (Usuario/Empleado) asociado")

    # -------- 2) Datos a imprimir --------
    # -------- 2) Datos a imprimir --------
    datos = {
        "nombre_paciente": paciente.nombre or "",
        "curp": paciente.curp or "",
        "fecha_nacimiento": paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else "",
        "direccion": paciente.direccion or "",
        "sexo": paciente.sexo or "",
        "edad": str(paciente.edad) if paciente.edad else "",
        "expediente": archivo.numero_expediente or "",
        "fecha": nota.fecha.strftime("%d/%m/%Y") if nota.fecha else "",
        "hora": nota.hora.strftime("%H:%M") if nota.hora else "",
        "peso": str(nota.peso) if nota.peso is not None else "",
        "talla": str(nota.talla) if nota.talla is not None else "",
        "ta": nota.ta or "",
        "fc": str(nota.fc) if nota.fc is not None else "",
        "fr": str(nota.fr) if nota.fr is not None else "",
        "temp": str(nota.temp) if nota.temp is not None else "",
        "cc": nota.cc or "",
        "spo2": str(nota.spo2) if nota.spo2 is not None else "",
        "glicemia": str(nota.glicemia) if nota.glicemia is not None else "",
        "imc": str(nota.imc) if nota.imc is not None else "",
        "medico": " ".join(
            x for x in [
                medico_emp.titulo,
                medico_emp.nombre,
                medico_emp.apellido_paterno,
                medico_emp.apellido_materno,
            ] if x
        ),
        "cedula": medico_emp.cedula or "",
        "antecedentes": ajustar_lineas("S.- " + (nota.antecedentes or ""), 65),
        "exploracion_fisica": ajustar_lineas("O.- " + (nota.exploracion_fisica or ""), 65),
        "laboratorio": ajustar_lineas("    " + (nota.laboratorio or ""), 65),
        "diagnostico": ajustar_lineas("A.- " + (nota.diagnostico or ""), 65),
        "plan": ajustar_lineas("P.- " + (nota.plan or ""), 65),
        "pronostico": ajustar_lineas(nota.pronostico, 65),
       
    }


    # -------- 3) Crear overlay con ReportLab --------
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # debug grid opcional
    if debug:
        can.setFont("Montserrat", 8)
        can.line(0, 0, letter[0], 0)
        can.line(0, 0, 0, letter[1])
        step = 20
        for y in range(0, int(letter[1]), step):
            can.drawString(2, y + 2, str(y))
        for x in range(0, int(letter[0]), step):
            can.drawString(x + 2, 2, str(x))

    # -------- 3a) Dibujar bloque concatenado --------
    campos_a_concatenar = [
        "antecedentes",
        "exploracion_fisica",
        "laboratorio",
        "diagnostico",
        "plan",
        "pronostico",
        
        
        
    ]

    texto_concatenado = []
    for campo in campos_a_concatenar:
        valor = datos.get(campo, [])
        if isinstance(valor, list):
            texto_concatenado.extend(valor)
        elif isinstance(valor, str) and valor.strip():
            texto_concatenado.append(valor.strip())
        texto_concatenado.append("")  # separador

    x, y = 150, 590
    line_height = 14
    can.setFont("Montserrat", 10)
    for i, linea in enumerate(texto_concatenado):
        can.drawString(x, y - i*line_height, linea)
        

    # -------- 3b) Dibujar los campos restantes --------
    coords = _build_coords()

    def put(field_key, text):
        if field_key not in coords:
            return
        x, y = coords[field_key]
        if isinstance(text, list):
            for i, line in enumerate(text):
                can.drawString(float(x), float(y - i*line_height), line)
        else:
            can.drawString(float(x), float(y), str(text) if text else "")

    for key, value in datos.items():
        if key not in campos_a_concatenar:
            put(key, value)

    can.save()
    packet.seek(0)

    # -------- 4) Mezclar overlay con la plantilla --------
    plantilla_path = os.path.join(current_app.root_path, "static", "medicos", "plantilla_nota.pdf")
    if not os.path.exists(plantilla_path):
        abort(500, description=f"No se encontró la plantilla en: {plantilla_path}")

    with open(plantilla_path, "rb") as f:
        plantilla_pdf = PdfReader(f)
        overlay_pdf = PdfReader(io.BytesIO(packet.getvalue()))
        output = PdfWriter()

        base_page = plantilla_pdf.pages[0]
        base_page.merge_page(overlay_pdf.pages[0])
        output.add_page(base_page)

        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)

    # -------- 5) Enviar PDF al navegador o descargar --------
    filename = f"nota_{id_nota}.pdf"
    return send_file(
        output_stream,
        as_attachment=download,
        download_name=filename,
        mimetype="application/pdf",
    )

@bp.route("/visor_plantilla")
@roles_required(['USUARIOMEDICO', 'Administrador'])
def visor_plantilla():
    """
    Visor interactivo para medir coordenadas de la plantilla PDF.
    """
    return render_template("medicos/visor_plantilla.html")

