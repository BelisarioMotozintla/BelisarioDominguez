#app/medicos/route.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file,jsonify, abort, current_app
from app import db
from flask_login import current_user  
from app.models.medicos import Consulta, NotaConsultaExterna
from app.models.archivo_clinico import Paciente
from app.models.personal import Servicio,Usuario,Roles
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
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante','SuperUsuario'])
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
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante','SuperUsuario'])
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

@bp.route('/consulta/<int:id_consulta>/nota/nueva', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante','SuperUsuario'])
def nueva_nota(id_consulta):
    consulta = Consulta.query.get_or_404(id_consulta)
    paciente = consulta.paciente

    # Solo si consulta abierta o admin
    if consulta.estado != "ABIERTA" and current_user.rol.nombre_rol != "Administrador":
        flash("Solo se puede agregar nota si la consulta está abierta o eres administrador", "danger")
        return redirect(url_for("medicos.menu_medico"))

    # Inicializar formulario
    form = NotaConsultaForm()

    # Determinar si es pasante
    es_pasante = current_user.rol.nombre_rol.upper() == "USUARIOPASANTE"

    # Lista de médicos responsables si es pasante
    medicos_responsables = []
    if es_pasante:
        medicos_responsables = Usuario.query.join(Roles).filter(Roles.nombre_rol=="USUARIOMEDICO").all()
        form.medico_responsable.choices = [(m.id_usuario, m.usuario) for m in medicos_responsables]

    # Prellenar signos vitales con última nota si existe
    nota_ultima = NotaConsultaExterna.query.filter_by(id_consulta=consulta.id_consulta)\
        .order_by(NotaConsultaExterna.fecha.desc(), NotaConsultaExterna.hora.desc()).first()
    if nota_ultima and request.method == 'GET':
        form.peso.data = nota_ultima.peso
        form.talla.data = nota_ultima.talla
        form.imc.data = nota_ultima.imc
        form.ta.data = nota_ultima.ta
        form.fc.data = nota_ultima.fc
        form.fr.data = nota_ultima.fr
        form.temp.data = nota_ultima.temp
        form.cc.data = nota_ultima.cc
        form.spo2.data = nota_ultima.spo2
        form.glicemia.data = nota_ultima.glicemia

    # Inicializar fecha y hora
    if request.method == "GET":
        if not form.fecha.data:
            form.fecha.data = datetime.utcnow().date()
        if not form.hora.data:
            form.hora.data = datetime.utcnow().time()

    if form.validate_on_submit():
        try:
            # Determinar usuario responsable
            if es_pasante:
                medico_responsable_id = form.medico_responsable.data
                if not medico_responsable_id:
                    flash("Debes seleccionar un médico responsable", "danger")
                    return redirect(request.url)
            else:
                medico_responsable_id = current_user.id_usuario

            # Calcular IMC
            imc_val = None
            if form.peso.data and form.talla.data and form.talla.data > 0:
                imc_val = round(float(form.peso.data) / (float(form.talla.data) ** 2), 2)

            # Crear nota
            nota = NotaConsultaExterna(
                id_consulta=consulta.id_consulta,
                id_servicio=form.id_servicio.data,
                fecha=form.fecha.data,
                hora=form.hora.data,
                usuario_id=medico_responsable_id,
                peso=form.peso.data,
                talla=form.talla.data,
                imc=imc_val,
                ta=form.ta.data,
                fc=form.fc.data,
                fr=form.fr.data,
                temp=form.temp.data,
                cc=form.cc.data,
                spo2=form.spo2.data,
                glicemia=form.glicemia.data,
                antecedentes=form.antecedentes.data,
                exploracion_fisica=form.exploracion_fisica.data,
                diagnostico=form.diagnostico.data,
                plan=form.plan.data,
                pronostico=form.pronostico.data,
                laboratorio=form.laboratorio.data,
            )

            db.session.add(nota)
            db.session.commit()
            flash("Nota registrada correctamente", "success")
            return redirect(url_for("medicos.ver_nota", id_nota=nota.id_nota))

        except Exception as e:
            db.session.rollback()
            flash("Ocurrió un error al guardar la nota", "danger")
            print("❌ Error:", e)

    return render_template(
        "medicos/nueva_nota.html",
        form=form,
        consulta=consulta,
        paciente=paciente,
        es_pasante=es_pasante,
        medicos_responsables=medicos_responsables
    )

@bp.route("/ver_nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante','SuperUsuario'])
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
        "medico": (350, 55),
        "cedula": (350, 45),
        "pasante": (350, 35),  # nueva coordenada para pasante
    }


def ajustar_lineas(texto, max_caracteres):
    if not texto:
        return []
    return textwrap.wrap(texto, max_caracteres)


@bp.route("/nota/<int:id_nota>")
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
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
            joinedload(NotaConsultaExterna.usuario)
            .joinedload(Usuario.empleado),
        )
        .filter(NotaConsultaExterna.id_nota == id_nota)
        .first()
    )

    if not nota:
        abort(404, description="Nota no encontrada")

    paciente = nota.consulta.paciente
    archivo = paciente.archivo_clinico[0] if paciente.archivo_clinico else None

    # Usuario médico responsable de la nota
    usuario_medico = nota.usuario
    medico_emp = usuario_medico.empleado if usuario_medico else None

    # Usuario pasante (quien abrió la consulta)
    usuario_pasante = nota.consulta.usuario
    pasante_emp = usuario_pasante.empleado if usuario_pasante else None

    if nota.id_servicio == 5:  # URGENCIAS
        expediente_num = archivo.numero_expediente if archivo is not None else "S/N"
    else:
        if archivo is None:
            abort(400, description="El paciente no tiene expediente asociado")
        expediente_num = archivo.numero_expediente

    if usuario_medico is None or medico_emp is None:
        abort(400, description="La nota no tiene médico (Usuario/Empleado) asociado")

    # Obtener nombre del servicio
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
        "expediente": expediente_num,
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
        "medico":"Médico: " + " ".join(
            x for x in [
                medico_emp.nombre,
                medico_emp.apellido_paterno,
                medico_emp.apellido_materno,
            ] if x
        ),
        "cedula": "Cédula:" + " " + medico_emp.cedula or "",
        "pasante": "Mpss: " + " ".join(
            x for x in [
                pasante_emp.nombre if pasante_emp else "",
                pasante_emp.apellido_paterno if pasante_emp else "",
                pasante_emp.apellido_materno if pasante_emp else "",
            ] if x
        ),
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
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
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
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def detalle_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    return render_template('notas_detalle.html', nota=nota)

@bp.route('/eliminar_nota/<int:id_nota>', methods=['POST'])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
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
