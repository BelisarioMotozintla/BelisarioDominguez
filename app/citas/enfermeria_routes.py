from operator import or_
from distro import like
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import timedelta
from app.citas import citas_bp
from app.models.archivo_clinico import ArchivoClinico, Paciente
from app.models.citas import Cita
from app.citas.forms import ProgramarCitaForm
from app.models.citas import hay_solapamiento
from app import db
from app.utils.helpers import roles_required
from sqlalchemy import String, cast
from sqlalchemy.orm import joinedload, aliased

@citas_bp.route('/enfermeria/buscar', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def solicitudes_pendientes():
    busqueda = request.args.get("q", "").strip()

    #
    # --- TABLA 1: CITAS PENDIENTES ---
    #
    citas_pendientes = (
        Cita.query
        .options(joinedload(Cita.paciente))
        .filter(Cita.estado == "pendiente")
        .filter(Cita.paciente_id.isnot(None))
        .order_by(Cita.fecha_hora.asc())
        .all()
    )

    #
    # --- TABLA 2: BUSCADOR EN ARCHIVO CLÍNICO (SIN RELACIÓN A CITAS) ---
    #
    resultados = []

    if busqueda:
       resultados = (
        ArchivoClinico.query
        .join(Paciente, ArchivoClinico.id_paciente == Paciente.id_paciente)
        .options(joinedload(ArchivoClinico.paciente))
        .filter(
            (Paciente.nombre.ilike(f"%{busqueda}%")) |
            (cast(Paciente.id_paciente, String).ilike(f"%{busqueda}%")) |
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{busqueda}%"))
        )
        .order_by(ArchivoClinico.fecha_creacion.desc())
        .limit(20)
        .all()
    )
    print("BUSCANDO:", busqueda)

    debug = (
        ArchivoClinico.query
        .filter(cast(ArchivoClinico.numero_expediente, String).ilike(f"%{busqueda}%"))
        .all()
    )
    print("ARCHIVOS ENCONTRADOS SIN JOIN:", len(debug))  

    return render_template(
        "lista_pacientes.html",
        pendientes=citas_pendientes,   # tabla 1
        resultados=resultados,         # tabla 2
        q=busqueda
    )
    


@citas_bp.route('/enfermeria/programar/<int:paciente_id>', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def programar(paciente_id):
    form = ProgramarCitaForm()
    paciente = Paciente.query.get_or_404(paciente_id)

    if form.validate_on_submit():
        start = form.fecha_hora.data
        end = start + timedelta(minutes=form.duracion_min.data)

        if hay_solapamiento(db.session, paciente.consultorio_id, start, end):
            flash("⚠ Choque con otra cita", "danger")
            return redirect(url_for('citas.programar', paciente_id=paciente_id))

        nueva = Cita(
            paciente_id=paciente.id_paciente,
            consultorio_id=paciente.consultorio_id,
            fecha_hora=start,
            duracion_min=form.duracion_min.data,
            creada_por=current_user.username
        )
        db.session.add(nueva)
        db.session.commit()

        flash("✔ Cita programada", "success")
        return redirect(url_for('citas.buscar_paciente'))

    return render_template('programar_cita.html', paciente=paciente, form=form)
