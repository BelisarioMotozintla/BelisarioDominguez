from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from datetime import date, datetime, timedelta
from app.citas import citas_bp
from app.utils.helpers import roles_required
from app.models.archivo_clinico import Paciente
from app.models.citas import Cita
from app.utils import db

# SOLO ME VAN  A APARECER
@citas_bp.route('/archivo/citas_hoy')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def citas_hoy():
    # Obtener fecha del formulario (YYYY-MM-DD)
    fecha_str = request.args.get("fecha", None)

    # Si NO hay fecha → mostrar todas las pendientes
    if not fecha_str:
        citas = Cita.query.filter_by(estado='pendiente')\
                          .order_by(Cita.fecha_hora.asc())\
                          .all()
        return render_template(
            'citas_dia_archivo.html',
            citas=citas,
            fecha=None
        )

    # Si hay fecha → convertir a rango del día
    fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    siguiente = fecha + timedelta(days=1)

    citas = Cita.query.filter(
        Cita.estado == 'pendiente',
        Cita.fecha_hora >= fecha,
        Cita.fecha_hora < siguiente
    ).order_by(Cita.fecha_hora.asc()).all()

    return render_template(
        'citas_dia_archivo.html',
        citas=citas,
        fecha=fecha_str
    )

@citas_bp.route('/registrar_paciente_desde_cita/<int:id_cita>', methods=['GET', 'POST'])
@login_required
def registrar_paciente_desde_cita(id_cita):
    cita = Cita.query.get_or_404(id_cita)

    if request.method == 'POST':
        paciente = Paciente(
            nombre=request.form['nombre'],
            curp=request.form['curp'],
            telefono=request.form.get('telefono'),
            direccion=request.form.get('direccion')
        )
        db.session.add(paciente)
        db.session.commit()

        # Asociar cita con paciente
        cita.paciente_id = paciente.id_paciente
        db.session.commit()

        flash("Paciente registrado y asociado a la cita", "success")
        return redirect(url_for('archivo_clinico.citas_dia'))

    return render_template('archivo_clinico/registro_paciente_desde_cita.html', cita=cita)
