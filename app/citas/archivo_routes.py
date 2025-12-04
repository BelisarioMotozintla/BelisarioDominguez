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


