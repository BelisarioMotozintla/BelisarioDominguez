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
    form = NotaConsultaForm()

    paciente = Paciente.query.get_or_404(id_paciente)
    form.id_paciente.data = paciente.id_paciente  # Preseleccionado

    # Obtener expediente único del paciente
    expediente = ArchivoClinico.query.filter_by(id_paciente=id_paciente).first()
    id_expediente = expediente.id_archivo if expediente else None

    if form.validate_on_submit():
        nota = NotaConsultaExterna(
            id_paciente=form.id_paciente.data,
            id_expediente=id_expediente,
            id_usuario=current_user.id_usuario,
            fecha=form.fecha.data,
            hora=form.hora.data,
            peso=form.peso.data,
            talla=form.talla.data,
            ta=form.ta.data,
            fc=form.fc.data,
            fr=form.fr.data,
            temp=form.temp.data,
            cc=form.cc.data,
            spo2=form.spo2.data,
            glicemia=form.glicemia.data,
            imc=form.imc.data,
            antecedentes=form.antecedentes.data,
            exploracion_fisica=form.exploracion_fisica.data,
            diagnostico=form.diagnostico.data,
            plan=form.plan.data,
            pronostico=form.pronostico.data,
            laboratorio=form.laboratorio.data,
        )
        db.session.add(nota)
        db.session.commit()
        flash('Nota registrada correctamente', 'success')
        return redirect(url_for('medicos.ver_nota', id_nota=nota.id_nota))

    if request.method == 'GET' and not form.fecha.data:
        form.fecha.data = datetime.utcnow().date()

    return render_template('medicos/nueva_nota.html', form=form, paciente=paciente, expediente=expediente)

@bp.route('/editar/<int:id_nota>', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def editar_nota(id_nota):
    # Obtener la nota
    nota = NotaConsultaExterna.query.get_or_404(id_nota)

    # Obtener paciente y expediente relacionados
    paciente = nota.paciente
    expediente = ArchivoClinico.query.get(nota.id_expediente) if nota.id_expediente else None

    # Inicializar formulario
    form = NotaConsultaForm(obj=nota)  # carga datos de la nota automáticamente

    # Cargar choices de pacientes
    form.id_paciente.choices = [(p.id_paciente, f"{p.nombre} {p.curp}") for p in Paciente.query.order_by(Paciente.nombre).all()]

    # Cargar choices de expedientes
    expedientes = ArchivoClinico.query.all()
    form.id_expediente.choices = [(e.id_archivo, f"{e.id_archivo} - {e.ubicacion_fisica[:40]}") for e in expedientes]
    form.id_expediente.choices.insert(0, (0, ' -- Ninguno -- '))

    if form.validate_on_submit():
        # Guardar cambios en la nota
        nota.id_paciente = form.id_paciente.data
        id_expediente = form.id_expediente.data or None
        nota.id_expediente = id_expediente if id_expediente != 0 else None

        nota.fecha = form.fecha.data
        nota.hora = form.hora.data
        nota.peso = form.peso.data
        nota.talla = form.talla.data
        nota.ta = form.ta.data
        nota.fc = form.fc.data
        nota.fr = form.fr.data
        nota.temp = form.temp.data
        nota.cc = form.cc.data
        nota.spo2 = form.spo2.data
        nota.glicemia = form.glicemia.data
        nota.imc = form.imc.data
        nota.antecedentes = form.antecedentes.data
        nota.exploracion_fisica = form.exploracion_fisica.data
        nota.diagnostico = form.diagnostico.data
        nota.plan = form.plan.data
        nota.pronostico = form.pronostico.data
        nota.laboratorio = form.laboratorio.data

        db.session.commit()
        flash('Nota actualizada correctamente', 'success')
        return redirect(url_for('medicos.ver_nota', id_nota=nota.id_nota))

    # Si es GET, prellenar paciente y expediente en el formulario
    if request.method == 'GET':
        form.id_paciente.data = nota.id_paciente
        form.id_expediente.data = nota.id_expediente or 0

        if not form.fecha.data:
            form.fecha.data = nota.fecha or datetime.utcnow().date()

    return render_template(
        'medicos/editar_nota.html',
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
#def notas_paciente(id_paciente):
#    notas = NotaConsultaExterna.query.filter_by(id_paciente=id_paciente).order_by(NotaConsultaExterna.fecha.desc()).all()
#    
#    data = [
#        {
#            "fecha": nota.fecha.strftime("%d/%m/%Y"),
#            "medico": nota.usuario.empleado.nombre if nota.usuario and nota.usuario.empleado else "Desconocido",
#            "diagnostico": nota.diagnostico
#        }
#        for nota in notas
#    ]
#    return jsonify(data)


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
        "medico": (350, 180),
        "cedula": (350, 160),
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
        "antecedentes": ajustar_lineas(nota.antecedentes, 65),
        "exploracion_fisica": ajustar_lineas(nota.exploracion_fisica, 65),
        "diagnostico": ajustar_lineas(nota.diagnostico, 90),
        "plan": ajustar_lineas(nota.plan, 60),
        "pronostico": ajustar_lineas(nota.pronostico, 90),
        "laboratorio": ajustar_lineas(nota.laboratorio, 90),
    }


    # -------- 3) Crear overlay con ReportLab --------
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # debug grid opcional
    if debug:
        can.setFont("Montserrat", 10)
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
        "diagnostico",
        "plan",
        "pronostico",
        "laboratorio",
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

