#app/consultas/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models.medicos import Consulta
from app.models.archivo_clinico import Paciente,ArchivoClinico   # suponiendo que lo tienes así
from app.utils.helpers import roles_required
from sqlalchemy import String, or_, cast, String
from flask_login import current_user
from datetime import datetime

bp = Blueprint('consultas', __name__, template_folder='templates/consultas')


# 📌 Lista de consultas
@bp.route('/')
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def listar_consultas():
    consultas = Consulta.query.order_by(Consulta.fecha.desc()).all()
    return render_template('consultas/lista.html', consultas=consultas)

@bp.route('/consultas/nueva', methods=['GET', 'POST'])
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def nueva_consulta():
    query = request.args.get("q", "").strip()

    # 1️⃣ Pacientes con expediente
    pacientes = db.session.query(Paciente).outerjoin(ArchivoClinico, Paciente.id_paciente == ArchivoClinico.id_paciente)
    if query:
        pacientes = pacientes.filter(
            or_(
                Paciente.nombre.ilike(f"%{query}%"),
                Paciente.curp.ilike(f"%{query}%"),
                cast(ArchivoClinico.numero_expediente, String).ilike(f"%{query}%")
            )
        )
    pacientes = pacientes.all()

    if request.method == 'POST':
        now = datetime.now()
        id_paciente = request.form.get('id_paciente')

        # Si es urgencia, crear paciente nuevo si no existe
        if id_paciente == "nuevo":
            nombre = request.form.get("nombre")
            curp = request.form.get("curp")
            fecha_nacimiento = request.form.get("fecha_nacimiento")
            sexo = request.form.get("sexo")
            paciente = Paciente(
                nombre=nombre,
                curp=curp,
                fecha_nacimiento=fecha_nacimiento,
                sexo=sexo
            )
            db.session.add(paciente)
            db.session.commit()
            id_paciente = paciente.id_paciente

        # Registrar consulta
        consulta = Consulta(
            id_paciente=id_paciente,
            id_usuario=current_user.id_usuario,
            fecha=now.date(),
            hora=now.time()
        )
        db.session.add(consulta)
        db.session.commit()

        flash("Consulta registrada con éxito", "success")
        return redirect(url_for("medicos.nueva_nota", id_consulta=consulta.id_consulta))

    return render_template("consultas/nueva.html", pacientes=pacientes, query=query)

@bp.route('/consultas/<int:id_consulta>')
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def ver_consultas(id_consulta):
    consulta = Consulta.query.get_or_404(id_consulta)
    notas = consulta.notas  # gracias a la relación back_populates
    return render_template(
        "consultas/ver_consulta.html",
        consulta=consulta,
        notas=notas
    )
# 📌 Detalle de una consulta
@bp.route('/<int:id_consulta>')
@roles_required(['USUARIOMEDICO', 'Administrador', 'UsuarioPasante'])
def detalle_consulta(id_consulta):
    consulta = Consulta.query.get_or_404(id_consulta)
    return render_template('detalle.html', consulta=consulta)

@bp.route('/editar/<int:id_consulta>', methods=['GET', 'POST'])
def editar_consulta(id_consulta):
    consulta = Consulta.query.get_or_404(id_consulta)
    if request.method == 'POST':
        # actualizar datos de la consulta
        db.session.commit()
        flash("Consulta actualizada", "success")
        return redirect(url_for('consultas.listar_consultas'))
    return render_template('consultas/editar.html', consulta=consulta)
