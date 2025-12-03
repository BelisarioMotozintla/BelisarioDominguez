from flask import Blueprint, render_template, request, flash, redirect, url_for
from datetime import datetime
from app.models.archivo_clinico import Paciente
from app.utils.extensions import  mail
from app.utils.db import db
from app.models.citas import Cita
from app.utils.helpers import roles_required
from flask_mail import Message
import qrcode
import io
import base64

bp = Blueprint('public', __name__, template_folder='templates/citas')


def generar_qr(texto):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return base64.b64encode(buf.getvalue()).decode("utf-8")


def enviar_correo_confirmacion(email, nombre, fecha, id_publico):
    if not email:
        return

    msg = Message(
        subject="Confirmación de cita",
        sender="belisario.dominguez.calidad@gmail.com",
        recipients=[email]
    )

    msg.body = f"""
Hola {nombre}.

Tu cita está registrada para el día {fecha.strftime('%d/%m/%Y %H:%M')}.

ID de cita: {id_publico}
"""
    if email:
        try:
            mail.send(msg)
        except Exception as e:
            print("Error enviando correo:", e)
   


@bp.route('/citas/nueva', methods=['GET', 'POST'])
def nueva_cita():
    if request.method == 'POST':

        nombre = request.form.get('nombre')
        curp = request.form.get('curp')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        fecha_hora_str = request.form.get('fecha_hora')
        motivo = request.form.get('motivo')

        if not nombre or not curp or not telefono or not fecha_hora_str:
            flash('Completa los campos obligatorios', 'danger')
            return redirect(url_for('public.nueva_cita'))

        try:
            fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M")
        except:
            flash("Fecha inválida", "danger")
            return redirect(url_for('public.nueva_cita'))

        # Validación de horario disponible
        existe = Cita.query.filter_by(fecha_hora=fecha_hora).first()
        if existe:
            flash("Ese horario ya está ocupado.", "danger")
            return redirect(url_for('public.nueva_cita'))

        # 🟦 1. Buscar si ya existe paciente con esa CURP
        paciente = Paciente.query.filter_by(curp=curp).first()

        # 🟧 2. Si existe → usar ese paciente en la cita
        if paciente:
            id_paciente = paciente.id_paciente
        else:
            id_paciente = None  # (Se registrará después en archivo clínico)

        # 🟩 3. Crear la cita (si existe paciente se asocia aquí mismo)
        cita = Cita(
            solicitante_nombre=nombre,
            curp=curp,
            telefono=telefono,
            email=email,
            fecha_hora=fecha_hora,
            motivo=motivo,
            paciente_id=id_paciente   # 👈 ASOCIACIÓN AUTOMÁTICA SI YA EXISTE
        )

        db.session.add(cita)
        db.session.commit()

        # Generar QR
        contenido_qr = f"CITA-{cita.uuid_publico} | {nombre} | {fecha_hora}"
        qr_base64 = generar_qr(contenido_qr)

        # Enviar correo
        enviar_correo_confirmacion(email, nombre, fecha_hora, cita.uuid_publico)

        flash('Solicitud recibida. Revisa los detalles abajo.', 'success')

        return render_template(
            "cita_confirmacion.html",
            nombre=nombre,
            fecha_hora=fecha_hora,
            id_cita=cita.uuid_publico,
            qr=qr_base64
        )

    return render_template("cita_nueva.html")

@bp.route('/detalle/<string:uuid>')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def detalle_cita(uuid):
    cita = Cita.query.filter_by(uuid_publico=uuid).first_or_404()

    # Generar nuevamente el QR (si lo quieres mostrar)
    contenido_qr = f"CITA-{cita.uuid_publico} | {cita.solicitante_nombre} | {cita.fecha_hora}"
    qr_base64 = generar_qr(contenido_qr)

    return render_template('cita_confirmacion.html',
                           nombre=cita.solicitante_nombre,
                           fecha_hora=cita.fecha_hora,
                           id_cita=cita.uuid_publico,
                           qr=qr_base64)
