from flask import Blueprint, current_app, flash, render_template, request, redirect, session, url_for, send_file
from app import db
from app.models import FolioCertificado,Paciente,Usuario,Empleado
from app.utils.helpers import roles_required
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from datetime import datetime
import io
import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


bp = Blueprint('certificado', __name__, template_folder='templates/certificado')

def formato_fecha_certificado(fecha=None):
    """
    Devuelve la fecha en el formato legal para el certificado:
    'Se extiende la presente a petición de la parte interesada a los 04 días del mes de SEPTIEMBRE del 2025 en el ej. Belisario Domínguez, Motozintla, Chiapas'
    """
    if fecha is None:
        fecha = datetime.now()
    
    dia = fecha.strftime('%d')  # día en dos dígitos
    meses = {
        1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
        5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
        9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
    }
    mes = meses[fecha.month]
    anio = fecha.year
    
    texto = f"Se extiende la presente a petición de la parte interesada a los {dia} días del mes de {mes} \ndel {anio} en el ej. Belisario Domínguez, Motozintla, Chiapas"
    return texto
def generar_certificado_pdf_con_plantilla(paciente, medico, folio, sangre, alergias):
    # 1️⃣ Crear overlay temporal con reportlab
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Coordenadas aproximadas (ajusta según tu plantilla)
    can.drawString(490, 665, f"000{folio}")
    can.drawString(200, 555, f"{medico.nombre} {medico.apellido_paterno} {medico.apellido_materno}")
    can.drawString(140, 505, f"{medico.cedula}")
    can.drawString(160, 415, paciente.nombre)
    can.drawString(155, 385, paciente.curp)
    sexo_texto = "Femenino" if paciente.sexo.upper() == "F" else "Masculino"
    can.drawString(190, 350, sexo_texto)
    can.drawString(305, 350, str(paciente.edad))
    sangre = f"{sangre}"
    # Separar grupo y factor
    grupo = sangre[:-1].upper()   # todo menos el último caracter → 'O'
    factor_signo = sangre[-1]     # último caracter → '+' o '-'
    factor = "POSITIVO" if factor_signo == "+" else "NEGATIVO"
    can.drawString(200, 315, f"{grupo}")
    can.drawString(290, 315, f"{factor}")
    can.drawString(440, 315, f"{alergias}")
    x = 76
    y = 230
    espacio_linea = 15 # distancia entre líneas
    texto=formato_fecha_certificado().split("\n")

    for linea in texto:
        can.drawString(x, y, linea)
        y -= espacio_linea  # bajar para la siguiente línea
    
    can.drawString(67, 170, f"Medico:{medico.nombre} {medico.apellido_paterno} {medico.apellido_materno}")
    
    can.save()

    packet.seek(0)

    # 2️⃣ Leer plantilla PDF
    plantilla_path = os.path.join(current_app.root_path, "static", "medicos", "certificado.pdf")
    template_pdf = PdfReader(plantilla_path)
    overlay_pdf = PdfReader(packet)
    output = PdfWriter()

    # 3️⃣ Combinar overlay + plantilla
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    output.add_page(page)

    # 4️⃣ Guardar en buffer
    buffer = io.BytesIO()
    output.write(buffer)
    buffer.seek(0)
    return buffer

def generar_certificado_prenupcial_pdf(paciente, medico, folio, sangre, alergias,VDRL,vih):
# 1️⃣ Crear overlay temporal con reportlab
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Coordenadas aproximadas (ajusta según tu plantilla)
    can.drawString(490, 665, f"000{folio}")
    can.drawString(200, 555, f"{medico.nombre} {medico.apellido_paterno} {medico.apellido_materno}")
    can.drawString(140, 505, f"{medico.cedula}")
    can.drawString(160, 430, paciente.nombre)
    can.drawString(155, 400, paciente.curp)
    sexo_texto = "Femenino" if paciente.sexo.upper() == "F" else "Masculino"
    can.drawString(190, 368, sexo_texto)
    can.drawString(315, 368, str(paciente.edad))
    sangre = f"{sangre}"
    # Separar grupo y factor
    grupo = sangre[:-1].upper()   # todo menos el último caracter → 'O'
    factor_signo = sangre[-1]     # último caracter → '+' o '-'
    factor = "POSITIVO" if factor_signo == "+" else "NEGATIVO"
    can.drawString(200, 305, f"{grupo}")
    can.drawString(290, 305, f"{factor}")
    can.drawString(440, 305, f"{alergias}")
    can.drawString(380, 283, f"{VDRL}")
    can.drawString(380, 260, f"{vih}")
    x = 76
    y = 230
    espacio_linea = 15 # distancia entre líneas
    texto=formato_fecha_certificado().split("\n")

    for linea in texto:
        can.drawString(x, y, linea)
        y -= espacio_linea  # bajar para la siguiente línea
    
    can.drawString(67, 160, f"Medico:{medico.nombre} {medico.apellido_paterno} {medico.apellido_materno}")
    
    can.save()

    packet.seek(0)

    # 2️⃣ Leer plantilla PDF
    plantilla_path = os.path.join(current_app.root_path, "static", "medicos", "prenupcial.pdf")
    template_pdf = PdfReader(plantilla_path)
    overlay_pdf = PdfReader(packet)
    output = PdfWriter()

    # 3️⃣ Combinar overlay + plantilla
    page = template_pdf.pages[0]
    page.merge_page(overlay_pdf.pages[0])
    output.add_page(page)

    # 4️⃣ Guardar en buffer
    buffer = io.BytesIO()
    output.write(buffer)
    buffer.seek(0)
    return buffer

# -------- Ruta para formulario (solo sangre y alergias) --------
@bp.route("/certificado/<int:id_paciente>/<int:id_medico>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante','SuperUsuario'])
def nuevo(id_paciente, id_medico):
    # Consultar paciente y médico
    paciente = Paciente.query.get_or_404(id_paciente)
    medico_usuario = Usuario.query.get_or_404(id_medico)
    
    if not medico_usuario.empleado:
        return "Error: Este usuario no tiene un empleado asociado", 400

    medico = medico_usuario.empleado  # objeto Empleado

    # Generar folio
    folio = FolioCertificado.generar_folio()

    # Determinar URL de Cancelar según rol
    rol = session.get('rol')
    if rol in ('USUARIOMEDICO', 'UsuarioPasante'):
        cancelar_url = url_for('medicos.menu_medico')
    else:
        cancelar_url = url_for('medicos.menu_medico')

    if request.method == "POST":
        tipo_certificado = request.form.get("tipo_certificado")
        sangre = request.form.get("sangre")
        alergias = request.form.get("alergias")
        vdrl=request.form.get("vdrl")
        vih=request.form.get("vih")
        if alergias == "otros":
            alergias = request.form.get("alergias_otros") or "Otros"

        # Generar PDF según tipo
        if tipo_certificado == "prenupcial":
            pdf_buffer = generar_certificado_prenupcial_pdf(paciente, medico, folio, sangre, alergias,vdrl,vih)
            
        else:
            pdf_buffer = generar_certificado_pdf_con_plantilla(paciente, medico, folio, sangre, alergias)

        # Guardar folio en base de datos
        folio_obj = FolioCertificado(folio=folio)
        db.session.add(folio_obj)
        db.session.commit()

        return send_file(pdf_buffer, as_attachment=True,
                         download_name=f"certificado_{folio}.pdf",
                         mimetype="application/pdf")

    return render_template("certificado/certificado_form.html",
                           paciente=paciente,
                           medico=medico,
                           folio=folio,
                           cancelar_url=cancelar_url)
                           #cancelar_url=cancelar_url)

#============================================================================folio======================================

# ---- LISTAR ----
@bp.route("/folios")
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def listar_folios():
    folios = FolioCertificado.query.order_by(FolioCertificado.folio).all()
    return render_template("certificado/listar.html", folios=folios)

# ---- ALTA ----
@bp.route("/folios/nuevo", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def nuevo_folio():
    if request.method == "POST":
        num = request.form.get("folio", type=int)

        if FolioCertificado.query.filter_by(folio=num).first():
            flash("Ese folio ya existe.", "danger")
            return redirect(url_for("certificado.nuevo_folio"))

        nuevo = FolioCertificado(folio=num)
        db.session.add(nuevo)
        db.session.commit()
        flash("Folio agregado correctamente.", "success")
        return redirect(url_for("certificado.listar_folios"))

    return render_template("certificado/nuevo.html")

# ---- EDITAR ----
@bp.route("/folios/editar/<int:id>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def editar_folio(id):
    folio = FolioCertificado.query.get_or_404(id)

    if request.method == "POST":
        nuevo_num = request.form.get("folio", type=int)

        # Validar duplicados
        if FolioCertificado.query.filter(FolioCertificado.folio == nuevo_num, FolioCertificado.id != id).first():
            flash("Ese folio ya existe.", "danger")
            return redirect(url_for("certificado.editar_folio", id=id))

        folio.folio = nuevo_num
        db.session.commit()
        flash("Folio actualizado.", "success")
        return redirect(url_for("certificado.listar_folios"))

    return render_template("certificado/editar.html", folio=folio)

# ---- ELIMINAR ----
@bp.route("/folios/eliminar/<int:id>", methods=["POST"])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def eliminar_folio(id):
    folio = FolioCertificado.query.get_or_404(id)
    db.session.delete(folio)
    db.session.commit()
    flash("Folio eliminado.", "info")
    return redirect(url_for("certificado.listar_folios"))
