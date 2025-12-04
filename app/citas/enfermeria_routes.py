from operator import or_
from distro import like
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.citas import citas_bp
from app.models.archivo_clinico import ArchivoClinico, Paciente
from app.models.citas import Cita, Consultorio
from app.citas.forms import ProgramarCitaForm
from app.models.citas import hay_solapamiento
from app import db
from app.utils.helpers import roles_required
from sqlalchemy import String, cast
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import func

from app.utils.mail_service import enviar_correo_confirmacion

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
    citas_confirmados = (
            Cita.query
            .options(joinedload(Cita.paciente))
            .filter(Cita.estado == "Confirmada")
            .filter(Cita.paciente_id.isnot(None))
            .order_by(Cita.fecha_hora.asc())
            .all()
        )
    archivos = ArchivoClinico.query.options(joinedload(ArchivoClinico.paciente))

    if busqueda:
        print("hola buscando desde enfermeria routes")
        archivos = archivos.join(Paciente).filter(
            (Paciente.nombre.ilike(f"%{busqueda}%")) |
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{busqueda}%"))
        )

    archivos = archivos.order_by(ArchivoClinico.fecha_creacion.desc()).limit(10).all()  # limitar a 50 registros

    return render_template(
        "lista_pacientes.html",
        pendientes=citas_pendientes,   # tabla 1         # tabla 2
        confirmadas=citas_confirmados, # tabla 3
        q=busqueda,
        archivos=archivos
    )
    
@citas_bp.route('/enfermeria/programar/<int:id_paciente>', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def programar(id_paciente):
    form = ProgramarCitaForm()
    paciente = Paciente.query.get_or_404(id_paciente)

    # Llenar consultorios
    form.consultorio_id.choices = [
        (c.id, c.nombre) for c in Consultorio.query.all()
    ]

    if form.validate_on_submit():
        start = datetime.combine(form.fecha.data, form.hora.data)
        end = start + timedelta(minutes=form.duracion_min.data)

        if hay_solapamiento(db.session, form.consultorio_id.data, start, end):
            flash("⚠ Choque con otra cita", "danger")
            return redirect(url_for('citas.programar', id_paciente=id_paciente))

        nueva = Cita(
            paciente_id=paciente.id_paciente,
            consultorio_id=form.consultorio_id.data,
            fecha_hora=start,
            duracion_min=form.duracion_min.data,
            creado_por=current_user.id_usuario,
            estado="Confirmada"   
        )

        db.session.add(nueva)
        db.session.commit()

       
        flash("✔ Cita programada", "success")
        return redirect(url_for('citas.solicitudes_pendientes'))

    return render_template("programar_cita.html", paciente=paciente, form=form)

@citas_bp.route('/confirmar/<int:id_cita>', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def editar_cita(id_cita):
    cita = Cita.query.get_or_404(id_cita)
    form = ProgramarCitaForm()

    # Llenar consultorios igual que en programar
    form.consultorio_id.choices = [
        (c.id, c.nombre) for c in Consultorio.query.all()
    ]

    # ➤ Prellenar campos al entrar por GET
    if request.method == "GET":
        form.consultorio_id.data = cita.consultorio_id
        form.fecha.data = cita.fecha_hora.date()
        form.hora.data = cita.fecha_hora.time()
        form.duracion_min.data = cita.duracion_min

    # ➤ Si viene el POST del formulario
    if form.validate_on_submit():
        email=cita.email
        nombre=cita.solicitante_nombre
        consultorio= Consultorio.query.get_or_404(form.consultorio_id.data)
        start = datetime.combine(form.fecha.data, form.hora.data)
        end = start + timedelta(minutes=form.duracion_min.data)

        # Validar solapamiento
        if hay_solapamiento(
            session=db.session,
            consultorio_id=form.consultorio_id.data,
            start_dt=start,
            end_dt=end,
            exclude_cita_id=id_cita
        ):
            flash("⚠ Choque con otra cita en ese horario", "danger")
            return redirect(url_for("citas.editar_cita", id_cita=id_cita))

        # ➤ Actualizar la misma cita
        cita.consultorio_id = form.consultorio_id.data
        cita.fecha_hora = start
        cita.duracion_min = form.duracion_min.data
        cita.estado = "Confirmada"

        db.session.commit()

         # Enviar correo
        subject="Confirmación de cita"
        mensaje = f"""
            Hola {nombre}.

            Se confirma su cita para el día {start.strftime('%d/%m/%Y %H:%M')}.

            en el consultorio {consultorio}

            ID de cita: {cita.uuid_publico}

            Gracias por su preferencia.
            """
        enviar_correo_confirmacion(email,mensaje,subject)
       

        flash("✔ Cita actualizada correctamente", "success")
        return redirect(url_for("citas.solicitudes_pendientes"))

    return render_template("editar_cita.html", form=form, cita=cita)

@citas_bp.route('/cancelar/<int:id_cita>', methods=['POST'])
@roles_required(['JefeEnfermeria'])
def cancelar_cita(id_cita):
    cita = Cita.query.get_or_404(id_cita)
    cita.estado = "cancelada"
    db.session.commit()

    flash("❌ La cita fue cancelada.", "warning")
    return redirect(url_for('citas.solicitudes_pendientes'))