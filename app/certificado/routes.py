from flask import Blueprint, render_template, request, redirect, url_for, send_file
from app import db
from app.models import FolioCertificado
from app.utils.helpers import roles_required
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from datetime import datetime
import io




bp = Blueprint('certificado', __name__, template_folder='templates/certificado')


@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def generar_certificado_pdf(paciente, medico, folio, sangre, alergias):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Justify", alignment=TA_JUSTIFY, leading=16))

    story = []

    story.append(Paragraph(f"<b>FOLIO No. {folio}</b>", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>CERTIFICADO MÉDICO</b>", styles["Title"]))
    story.append(Spacer(1, 20))

    texto = f"""
    A QUIEN CORRESPONDA:<br/><br/>
    El suscrito Médico Cirujano <b>{medico.nombre}</b>, con cédula profesional {medico.cedula}, 
    adscrito a IMSS-BIENESTAR, certifica que el(la) C. <b>{paciente.nombre}</b>, 
    con CURP <b>{paciente.curp}</b>, del sexo {paciente.sexo}, de {paciente.edad} años, 
    quien posterior a una valoración médica, se encuentra físicamente y mentalmente sano(a).<br/><br/>
    GRUPO SANGUÍNEO: <b>{sangre}</b><br/>
    ALERGIAS: <b>{alergias}</b><br/><br/>
    Se expide la presente a petición del interesado(a) para fines personales y/o laborales.<br/><br/>
    {datetime.now().strftime('%d/%m/%Y')} – {medico.lugar}
    """

    story.append(Paragraph(texto, styles["Justify"]))
    story.append(Spacer(1, 50))

    story.append(Paragraph(f"<b>{medico.nombre}</b><br/>Médico Responsable", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

# -------- Ruta para formulario (solo sangre y alergias) --------
@bp.route("/certificado/<int:id_paciente>/<int:id_medico>/<int:folio>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def certificado(id_paciente, id_medico, folio):
    # Aquí consultas en la base de datos
    paciente = Paciente.query.get_or_404(id_paciente)
    medico = Medico.query.get_or_404(id_medico)

    if request.method == "POST":
        sangre = request.form.get("sangre")
        alergias = request.form.get("alergias") or "Ninguna"

        pdf_buffer = generar_certificado_pdf(paciente, medico, folio, sangre, alergias)
        return send_file(pdf_buffer, as_attachment=True,
                         download_name=f"certificado_{folio}.pdf",
                         mimetype="application/pdf")

    return render_template("certificado_form.html", paciente=paciente, folio=folio)

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
