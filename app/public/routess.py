#app/public/routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.utils.db import db
from app.models.citas import Cita
from datetime import datetime

bp = Blueprint('public', __name__, template_folder='templates/citas')

@bp.route('/citas/nueva', methods=['GET', 'POST'])
def nueva_cita():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        email = request.form.get('email')
        fecha_hora_str = request.form.get('fecha_hora')
        motivo = request.form.get('motivo')

        # Validaciones
        if not nombre or not telefono or not fecha_hora_str:
            flash('Completa los campos obligatorios', 'danger')
            return redirect(url_for('public.nueva_cita'))

        # Parseo seguro de fecha
        try:
            fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Formato de fecha no válido.", "danger")
            return redirect(url_for('public.nueva_cita'))
        
        existe = Cita.query.filter_by(fecha_hora=fecha_hora).first()
        if existe:
            flash("Ese horario ya está ocupado. Por favor elige otro.", "danger")
            return redirect(url_for('public.nueva_cita'))
        # Crear cita
        cita = Cita(
            solicitante_nombre=nombre,
            telefono=telefono,
            email=email,
            fecha_hora=fecha_hora,
            motivo=motivo,
            estado='pendiente'
        )
        db.session.add(cita)
        db.session.commit()

        # Flash visible en la plantilla de confirmación
        flash('Solicitud de cita recibida. En breve le confirmaremos.', 'success')

        return render_template(
            "cita_confirmacion.html",
            nombre=nombre,
            fecha_hora=fecha_hora
        )

    return render_template('cita_nueva.html')
