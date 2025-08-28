#app/medicos/route.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file,jsonify, abort, current_app
from app import db
from flask_login import current_user  
from app.models.medicos import Consulta, NotaConsultaExterna
from app.models.archivo_clinico import Paciente
from app.models.personal import Servicio,Usuario
from app.medicos.forms import NotaConsultaForm
from app.utils.helpers import roles_required
from sqlalchemy import String, or_
from sqlalchemy.orm import joinedload
from app.utils.validaciones_nota import campos_validos_nota_medica,get_time
from datetime import datetime, date, time  
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io
import os
import textwrap
bp = Blueprint('medicos', __name__, template_folder='templates/medicos')


@bp.route('/menu', methods=['GET'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def menu_medico():
    query = request.args.get('q', '')

    consultas = Consulta.query.join(Paciente).filter(
        (Paciente.nombre.ilike(f"%{query}%")) |
        (Paciente.curp.ilike(f"%{query}%")) |
        (Consulta.id_consulta.cast(String).ilike(f"%{query}%"))
    ).order_by(Consulta.fecha.desc()).all()

    return render_template(
        'medicos/menu_medico.html',
        consultas=consultas,
        query=query
    )


# 📌 Lista de notas de una consulta
@bp.route('/notas/<int:id_consulta>')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def listar_notas(id_consulta):
    consulta = Consulta.query.get_or_404(id_consulta)
    notas = consulta.notas
    volver_url = request.referrer or url_for('medicos.listar_notas', id_consulta=id_consulta)

    return render_template(
        "medicos/notas_lista.html",
        consulta=consulta,
        notas=notas,
        volver_url=volver_url
    )

def calcular_imc(peso, talla):
    try:
        if peso is not None and talla not in [None, 0]:
            return round(peso / (talla ** 2), 2)
    except Exception:
        return None
    return None
def safe_str(val):
    if isinstance(val, str):
        return val.strip()
    return val if val is not None else ""

@bp.route('/<int:id_consulta>/nota/nueva', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def nueva_nota(id_consulta):
    # Obtener consulta y paciente
    consulta = Consulta.query.get_or_404(id_consulta)
    paciente = consulta.paciente

    # Bloquear acceso si la consulta no está abierta y el usuario no es admin
    if consulta.estado != "ABIERTA" and current_user.rol.nombre_rol != "Administrador":
        flash("Solo se puede agregar nota si la consulta está abierta o eres administrador", "danger")
        return redirect(url_for("medicos.menu_medico"))

    # Servicios disponibles
    servicios = Servicio.query.filter_by(area='Paciente').all()
    choices_servicios = [(s.id_servicio, s.nombre_servicio) for s in servicios]
    if not choices_servicios:
        choices_servicios = [(0, 'Sin servicio')]

    # Inicializar formulario
    form = NotaConsultaForm()
    form.id_servicio.choices = choices_servicios  # importante asignarlo antes de validate_on_submit

    # Última nota para prellenar signos vitales
    notas_anteriores = NotaConsultaExterna.query.filter_by(
        id_consulta=consulta.id_consulta
    ).order_by(NotaConsultaExterna.fecha.desc(), NotaConsultaExterna.hora.desc()).first()

    if notas_anteriores and request.method == 'GET':
        form.peso.data = notas_anteriores.peso
        form.talla.data = notas_anteriores.talla
        form.imc.data = notas_anteriores.imc
        form.ta.data = notas_anteriores.ta
        form.fc.data = notas_anteriores.fc
        form.fr.data = notas_anteriores.fr
        form.temp.data = notas_anteriores.temp
        form.cc.data = notas_anteriores.cc
        form.spo2.data = notas_anteriores.spo2
        form.glicemia.data = notas_anteriores.glicemia

    # Inicializar fecha y hora en GET
    if request.method == "GET":
        if not form.fecha.data:
            form.fecha.data = datetime.utcnow().date()
        if not form.hora.data:
            form.hora.data = datetime.utcnow().time()

    # Depuración: imprimir datos POST
    if request.method == "POST":
        print("=== Datos POST enviados ===")
        print("Form crudo:", request.form)
        print("Form procesado:", form.data)
        print("Choices de servicio:", form.id_servicio.choices)
        print("==========================")
        print("Método:", request.method)
        print("Datos del formulario:", request.form)
        print("Choices actuales:", form.id_servicio.choices)
    # POST: guardar nota
    if form.validate_on_submit():
    
        datos = form.data
        errores, campos = campos_validos_nota_medica(datos)
        print("=== Imprimiendo servicio seleccionado ===")
        print("Servicio seleccionado:", form.id_servicio.data)
        if errores:
            for e in errores:
                flash(e, "danger")
        else:
            # Calcular IMC
            imc_val = calcular_imc(campos['peso'], campos['talla'])

            # Hora segura
            hora_val = form.hora.data
            if not isinstance(hora_val, time):
                hora_val = get_time(datos, 'hora') or datetime.utcnow().time()

            # Evitar guardar un servicio inválido
            if form.id_servicio.data == 0:
                flash("Debe seleccionar un servicio válido", "danger")
            else:
                try:
                    nota = NotaConsultaExterna(
                        id_consulta=consulta.id_consulta,
                        id_servicio=form.id_servicio.data,
                        fecha=form.fecha.data,
                        hora=hora_val,
                        peso=campos['peso'],
                        talla=campos['talla'],
                        imc=imc_val,
                        ta=campos['ta'],
                        fc=campos['fc'],
                        fr=campos['fr'],
                        temp=campos['temp'],
                        cc=campos['cc'],
                        spo2=campos['spo2'],
                        glicemia=campos['glicemia'],
                        presentacion=safe_str(form.presentacion.data),
                        antecedentes=safe_str(form.antecedentes.data),
                        exploracion_fisica=safe_str(form.exploracion_fisica.data),
                        diagnostico=safe_str(form.diagnostico.data),
                        plan=safe_str(form.plan.data),
                        pronostico=safe_str(form.pronostico.data),
                        laboratorio=safe_str(form.laboratorio.data),
                    )
                    print("Servicio seleccionado:", nota.id_servicio)

                    db.session.add(nota)
                    db.session.commit()

                    # Cambiar estado del expediente a cerrado
                   
                    flash("Nota registrada correctamente", "success")
                    return redirect(url_for("medicos.ver_nota", id_nota=nota.id_nota))

                except Exception as e:
                    db.session.rollback()
                    flash("Ocurrió un error al guardar la nota", "danger")
                    print("❌ Error al guardar en BD:", e)

    # Renderizar template
    return render_template(
        "medicos/nueva_nota.html",
        form=form,
        consulta=consulta,
        paciente=paciente
    )

@bp.route("/ver_nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador'])
def ver_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    # Obtener la consulta relacionada
    consulta = Consulta.query.get(nota.id_consulta)
    
    # Paciente
    paciente = consulta.paciente if consulta else None
    
    # Médico
    medico = consulta.usuario.empleado if consulta and consulta.usuario else None
    return render_template(
        'medicos/ver_nota.html',
        nota=nota,
        paciente=paciente,
        medico=medico,
        volver_url = request.referrer or url_for('medicos.listar_notas', id_consulta=nota.id_consulta)
    )
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

    # Registrar fuentes Montserrat
    font_dir = os.path.join(current_app.root_path, "static", "fonts")
    montserrat_regular = os.path.join(font_dir, "Montserrat-Regular.ttf")
    montserrat_bold = os.path.join(font_dir, "Montserrat-Bold.ttf")
    pdfmetrics.registerFont(TTFont("Montserrat", montserrat_regular))
    pdfmetrics.registerFont(TTFont("Montserrat-Bold", montserrat_bold))

    # Consulta con joins
    nota = (
        db.session.query(NotaConsultaExterna)
        .options(
            joinedload(NotaConsultaExterna.consulta)
            .joinedload(Consulta.paciente)
            .joinedload(Paciente.archivo_clinico),
            joinedload(NotaConsultaExterna.consulta)
            .joinedload(Consulta.usuario)
            .joinedload(Usuario.empleado),
        )
        .filter(NotaConsultaExterna.id_nota == id_nota)
        .first()
    )

    if not nota:
        abort(404, description="Nota no encontrada")

    paciente = nota.consulta.paciente
    archivo = paciente.archivo_clinico[0] if paciente.archivo_clinico else None
    usuario_medico = nota.consulta.usuario
    medico_emp = usuario_medico.empleado if usuario_medico else None
    
    if nota.id_servicio == 5:  # URGENCIAS
        expediente_num = archivo.numero_expediente if archivo is not None else "S/N"
    else:
        if archivo is None:
            abort(400, description="El paciente no tiene expediente asociado")
        expediente_num = archivo.numero_expediente

    if usuario_medico is None or medico_emp is None:
        abort(400, description="La nota no tiene médico (Usuario/Empleado) asociado")

    # Obtener nombre del servicio
    from app.models.personal import Servicio
    servicio_obj = Servicio.query.get(nota.id_servicio)
    nombre_servicio = servicio_obj.nombre_servicio if servicio_obj else "Consulta"

    # Datos a imprimir
    datos = {
        "nombre_servicio": nombre_servicio or "",
        "nombre_paciente": paciente.nombre or "",
        "curp": paciente.curp or "",
        "fecha_nacimiento": paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente.fecha_nacimiento else "",
        "direccion": paciente.direccion or "",
        "sexo": paciente.sexo or "",
        "edad": str(paciente.edad) if paciente.edad else "",
        "expediente":  expediente_num,
        "fecha": nota.fecha.strftime("%d/%m/%Y") if nota.fecha else "",
        "hora": nota.hora.strftime("%H:%M") if nota.hora else "",
        "peso": str(nota.peso) if nota.peso is not None else "",
        "talla": str(nota.talla) if nota.talla is not None else "",
        "ta": nota.ta or "",
        "fc": str(nota.fc) if nota.fc is not None else "",
        "fr": str(nota.fr) if nota.fr is not None else "",
        "temp": str(nota.temp) if nota.temp is not None else "",
        "cc": str(nota.cc) if nota.cc is not None else "",
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
        "presentacion": ajustar_lineas("P.- " + (nota.presentacion or ""), 65),
        "antecedentes": ajustar_lineas("S.- " + (nota.antecedentes or ""), 65),
        "exploracion_fisica": ajustar_lineas("O.- " + (nota.exploracion_fisica or ""), 65),
        "laboratorio": ajustar_lineas("    " + (nota.laboratorio or ""), 65),
        "diagnostico": ajustar_lineas("A.- " + (nota.diagnostico or ""), 65),
        "plan": ajustar_lineas("P.- " + (nota.plan or ""), 65),
        "pronostico": ajustar_lineas(nota.pronostico or "", 65),
    }

    # Crear overlay PDF
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Encabezado del servicio
    can.setFont("Montserrat-Bold", 12)
    can.drawString(220, 700, f"NOTA DE {nombre_servicio}")

    if debug:
        can.setFont("Montserrat", 8)
        can.line(0, 0, letter[0], 0)
        can.line(0, 0, 0, letter[1])
        step = 20
        for y in range(0, int(letter[1]), step):
            can.drawString(2, y + 2, str(y))
        for x in range(0, int(letter[0]), step):
            can.drawString(x + 2, 2, str(x))

    # Campos concatenados
    campos_a_concatenar = [
        "presentacion",
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

    # Campos individuales
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

    # Mezclar overlay con plantilla
    plantilla_path = _plantilla_path()
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

    filename = f"nota_{id_nota}.pdf"
    return send_file(
        output_stream,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


@bp.route('/editar/<int:id_nota>', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def editar_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    consulta = nota.consulta
    paciente = consulta.paciente if consulta else None
    
    servicio_actual = nota.servicio

    form = NotaConsultaForm(obj=nota)

    # Solo services
    form.id_servicio.choices = [
        (s.id_servicio, s.nombre_servicio)
        for s in Servicio.query.filter_by(area='Paciente').order_by(Servicio.nombre_servicio).all()
    ]

    if form.validate_on_submit():
        datos = form.data
        errores, datos_validados = campos_validos_nota_medica(datos)

        if errores:
            for e in errores:
                flash(e, "danger")
        else:
            nota.id_servicio = form.id_servicio.data
            nota.fecha = datos_validados['fecha']
            nota.hora = form.hora.data
            nota.peso = datos_validados['peso']
            nota.talla = datos_validados['talla']
            nota.imc = calcular_imc(nota.peso, nota.talla)
            nota.ta = datos_validados['ta']
            nota.fc = datos_validados['fc']
            nota.fr = datos_validados['fr']
            nota.temp = datos_validados['temp']
            nota.cc = datos_validados['cc']
            nota.spo2 = datos_validados['spo2']
            nota.glicemia = datos_validados['glicemia']
            nota.presentacion = datos_validados['presentacion']
            nota.antecedentes = datos_validados['antecedentes']
            nota.exploracion_fisica = datos_validados['exploracion_fisica']
            nota.diagnostico = datos_validados['diagnostico']
            nota.plan = datos_validados['plan']
            nota.pronostico = datos_validados['pronostico']
            nota.laboratorio = datos_validados['laboratorio']

            db.session.commit()
            flash("Nota actualizada correctamente", "success")
            return redirect(url_for("medicos.ver_nota", id_nota=nota.id_nota))

    if request.method == 'GET':
        form.id_servicio.data = nota.id_servicio
        if not form.fecha.data:
            form.fecha.data = nota.fecha or datetime.utcnow().date()
        if not form.hora.data:
            form.hora.data = nota.hora or datetime.utcnow().time()

    return render_template(
        "medicos/editar_nota.html",
        form=form,
        paciente=paciente,
        servicio=servicio_actual,
        nota=nota
    )
    
    
# 📌 Detalle de una nota
@bp.route('/notas/detalle/<int:id_nota>')
@roles_required(['USUARIOMEDICO', 'Administrador'])
def detalle_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    return render_template('notas_detalle.html', nota=nota)

@bp.route('/eliminar_nota/<int:id_nota>', methods=['POST'])
@roles_required(['USUARIOMEDICO', 'Administrador'])
def eliminar_nota(id_nota):
    # Obtener la nota y la consulta asociada
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    consulta = nota.consulta

    try:
        db.session.delete(nota)
        db.session.commit()
        flash('Nota eliminada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la nota: {str(e)}', 'danger')
        return redirect(url_for('medicos.menu_medico'))

    # Recargar la consulta para evitar DetachedInstanceError
    if consulta:
        consulta = Consulta.query.get(consulta.id_consulta)
        if not consulta.notas:  # No quedan notas
            try:
                db.session.delete(consulta)
                db.session.commit()
                flash('Consulta eliminada porque no tenía más notas.', 'info')
                return redirect(url_for('medicos.menu_medico'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al eliminar la consulta: {str(e)}', 'danger')
                return redirect(url_for('medicos.menu_medico'))

    # Si aún quedan notas, redirigir a la lista de notas de esa consulta
    return redirect(url_for('medicos.listar_notas', id_consulta=consulta.id_consulta))
