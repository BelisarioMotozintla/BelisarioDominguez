import textwrap
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file,jsonify, abort, current_app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from PyPDF2 import PdfReader, PdfWriter
from sqlalchemy.orm import joinedload
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
    notas = NotaConsultaExterna.query.order_by(NotaConsultaExterna.fecha.desc()).all()

    # Calcular edad de cada paciente
    for nota in notas:
        if nota.paciente and nota.paciente.fecha_nacimiento:
            nota.edad = (date.today() - nota.paciente.fecha_nacimiento).days // 365
        else:
            nota.edad = None

    return render_template('medicos/index.html', notas=notas)

@bp.route('/nueva', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def nueva_nota():
    form = NotaConsultaForm()
    # cargar choices para pacientes
    form.id_paciente.choices = [(p.id_paciente, f"{p.nombre} {p.curp}") for p in Paciente.query.order_by(Paciente.nombre).all()]
    
    # cargar choices para expedientes
    expedientes = ArchivoClinico.query.all()
    form.id_expediente.choices = [(e.id_archivo, f"{e.id_archivo} - {e.ubicacion_fisica[:40]}") for e in expedientes]
    form.id_expediente.choices.insert(0, (0, ' -- Ninguno -- '))

    if form.validate_on_submit():
        id_expediente = form.id_expediente.data or None
        if id_expediente == 0:
            id_expediente = None

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

    # default fecha a hoy si es GET y no tiene fecha
    if request.method == 'GET' and not form.fecha.data:
        form.fecha.data = datetime.utcnow().date()

    return render_template('medicos/nueva_nota.html', form=form)

@bp.route('/editar/<int:id_nota>', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def editar_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)

    # Crear el formulario precargado con los datos de la nota
    form = NotaConsultaForm(obj=nota)

    if form.validate_on_submit():
        # Rellenar el objeto nota con los datos del formulario
        form.populate_obj(nota)
        db.session.commit()
        flash('Nota actualizada correctamente', 'success')
        return redirect(url_for('medicos.ver_nota', id_nota=nota.id_nota))

    return render_template('medicos/editar_nota.html', form=form, nota=nota)

@bp.route('/ver/<int:id_nota>')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def ver_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)

    return render_template('medicos/ver_nota.html', nota=nota)

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

def _plantilla_path():
    return os.path.join(current_app.root_path, "static", "medicos", "plantilla_nota.pdf")

def _build_coords():
    return {
        "nombre_paciente": (150, 655),
        "edad": (440, 655),
        "diagnostico": (150, 390),
        "expediente": (150, 635),
        "fecha": (85, 590),
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
        "antecedentes": (150, 590),
        "exploracion_fisica": (150, 515),
        "plan": (150, 300),
        "pronostico": (150, 250),
        "laboratorio": (150, 200),
        
        
    }

@bp.route("/nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador'])
def generar_nota_pdf(id_nota: int):
    """
    Genera el PDF de la nota:
      - Usa plantilla como fondo.
      - Dibuja datos por encima.
      - ?debug=1 para malla de coordenadas.
      - ?dl=0 para mostrar en navegador (inline), por defecto descarga (?dl=1).
    """
    
    debug = request.args.get("debug", "0") == "1"
    download = request.args.get("dl", "1") != "0"  # dl=0 => mostrar inline

    # -------- 1) Consulta con joins
    nota = (
        db.session.query(NotaConsultaExterna)
        .options(
            joinedload(NotaConsultaExterna.paciente)
            .joinedload(Paciente.archivo_clinico),
            joinedload(NotaConsultaExterna.usuario)
            .joinedload(Usuario.empleado),
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
    
    def ajustar_lineas(texto, max_caracteres):
        """
        Recorta o divide el texto en líneas de máximo `max_caracteres` caracteres
        respetando palabras completas.
        """
        if not texto:
            return ""
        import textwrap
    return "\n".join(textwrap.wrap(texto, max_caracteres))
    
    # -------- 2) Datos a imprimir
    datos = {
        "nombre_paciente": paciente.nombre or "",
        "edad": str(paciente.edad) if paciente.edad else "",
        "diagnostico": nota.diagnostico or "",
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
        "antecedentes": ajustar_lineas(nota.antecedentes, 90),
        "exploracion_fisica": ajustar_lineas(nota.exploracion_fisica, 90),
        "plan": ajustar_lineas(nota.plan, 90),
        "pronostico": ajustar_lineas(nota.pronostico, 90),
        "laboratorio": ajustar_lineas(nota.laboratorio, 90),
    }


    # -------- 3) Crear overlay con ReportLab
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    if debug:
        can.setFont("Helvetica", 6)
        can.line(0, 0, letter[0], 0)
        can.line(0, 0, 0, letter[1])
        step = 20
        for y in range(0, int(letter[1]), step):
            can.drawString(2, y + 2, str(y))
        for x in range(0, int(letter[0]), step):
            can.drawString(x + 2, 2, str(x))

    coords = _build_coords()
    can.setFont("Helvetica", 12)

    def put(field_key, text):
        if field_key not in coords:
            return
        x, y = coords[field_key]
        
        if isinstance(text, list):  # varias líneas
            line_height = 14  # separación vertical entre líneas
            
            for i, line in enumerate(text):
                can.drawString(float(x), float(y - (i * line_height)), line)
        else:
            can.drawString(float(x), float(y), str(text) if text is not None else "")


    for key, value in datos.items():
        put(key, value)

    can.save()
    packet.seek(0)

    # -------- 4) Mezclar overlay con la plantilla
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

    # -------- 5) Enviar PDF al navegador o descargar
    filename = f"nota_{id_nota}.pdf"
    return send_file(
        output_stream,
        as_attachment=download,          # True = descargar, False = mostrar en navegador
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

