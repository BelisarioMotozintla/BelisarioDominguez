from flask import Blueprint, current_app, render_template, request, redirect, flash, session, url_for
from flask_login import login_required,current_user
from app.models import Usuario
from app.models.archivo_clinico import UnidadSalud
from app.models.personal import Empleado, Puesto, Servicio, Turno
from app.utils.db import db
from app.utils.helpers import usuarios_con_rol_requerido,roles_required  # tu decorador para control de acceso
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads/fotos_empleado"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

bp = Blueprint('perfil', __name__, template_folder='templates')

@bp.route("/")
@usuarios_con_rol_requerido
def perfil_home():
    uid = session.get('_user_id')

    if not uid:
        flash("Inicia sesión primero.")
        return redirect(url_for('auth.login'))

 #   usuario = Usuario.query.get(uid)
 #   print("session del usuario")
 #   print(uid)
 #   print(usuario.id_empleado)

    # Si NO está asociado a un empleado:
   # empleado= Usuario.query.get(uid)
    if not current_user.empleado:
        flash("Completa tu información de empleado.", "warning")
        return redirect(url_for("perfil.capturar_empleado"))
    
    # Si ya tiene empleado → ver perfil
    return redirect(url_for("perfil.ver_perfil"))

@bp.route("/capturar", methods=["GET", "POST"])
@usuarios_con_rol_requerido
def capturar_empleado():

    if current_user.empleado:
        return redirect(url_for("perfil.ver_perfil"))

    if request.method == "POST":

        # FOTO
        archivo = request.files.get("foto")
        ruta_foto = None

        if archivo and archivo.filename != "":
            filename = secure_filename(archivo.filename)
            ruta = os.path.join(UPLOAD_FOLDER, filename)
            archivo.save(ruta)
            ruta_foto = f"/{ruta}"

        emp = Empleado(
            nombre=request.form.get("nombre"),
            apellido_paterno=request.form.get("apellido_paterno"),
            apellido_materno=request.form.get("apellido_materno"),
            curp=request.form.get("curp"),
            rfc=request.form.get("rfc"),
            email=request.form.get("email"),
            telefono=request.form.get("telefono"),
            direccion=request.form.get("direccion"),
            foto=ruta_foto
        )

        db.session.add(emp)
        db.session.flush()

        current_user.id_empleado = emp.id_empleado
        db.session.commit()

        flash("Datos de empleado registrados correctamente.", "success")
        return redirect(url_for("perfil.ver_perfil"))

    return render_template("capturar_empleado.html")

@bp.route("/ver")
@usuarios_con_rol_requerido
def ver_perfil():
    empleado = current_user.empleado
    print("Puesto:", empleado.id_puesto)
    print("Turno:", empleado.id_turno)
    print("Unidad:", empleado.id_unidad)
    print("Servicio:", empleado.id_servicio)
    return render_template("ver.html", empleado=empleado)




@bp.route("/editar", methods=["GET", "POST"])
@usuarios_con_rol_requerido
def editar_perfil():
    empleado = current_user.empleado

    # Si el usuario no tiene empleado vinculado, no puede editar
    if not empleado:
        flash("Aún no tienes un registro de empleado asignado.", "warning")
        return redirect(url_for("perfil.ver_perfil"))

    # Cargar catálogos
    puestos = Puesto.query.all()
    turnos = Turno.query.all()
    unidades = UnidadSalud.query.all()
    servicios = Servicio.query.all()

    if request.method == "POST":
        # Datos personales
        empleado.nombre = request.form.get("nombre")
        empleado.apellido_paterno = request.form.get("apellido_paterno")
        empleado.apellido_materno = request.form.get("apellido_materno")

        # Laborales
        empleado.tipo_trabajador = request.form.get("tipo_trabajador")
        empleado.no_biometrico = request.form.get("no_biometrico")
        empleado.fecha_ingreso = request.form.get("fecha_ingreso")
        empleado.horario = request.form.get("horario")
        empleado.dias_laborables = request.form.get("dias_laborables")
        empleado.horas_laborales = request.form.get("horas_laborales")

        # Contacto
        empleado.email = request.form.get("email")
        empleado.telefono = request.form.get("telefono")
        empleado.direccion = request.form.get("direccion")

        # Adscripción
        empleado.id_puesto = request.form.get("id_puesto")
        empleado.id_turno = request.form.get("id_turno")
        empleado.id_unidad = request.form.get("id_unidad")
        empleado.id_servicio = request.form.get("id_servicio")

        db.session.commit()

        flash("Datos actualizados correctamente.", "success")
        return redirect(url_for("perfil.ver_perfil"))

    return render_template(
        "editar.html",
        empleado=empleado,
        puestos=puestos,
        turnos=turnos,
        unidades=unidades,
        servicios=servicios
    )



@bp.route("/subir_foto", methods=["POST"])
@usuarios_con_rol_requerido
def subir_foto():
    empleado = current_user.empleado
    archivo = request.files.get("foto")

    if not archivo:
        flash("Selecciona una foto.", "warning")
        return redirect(url_for("perfil.ver_perfil"))

    # Nombre único por empleado
    filename = f"empleado_{empleado.id_empleado}.jpg"

    # Ruta física real dentro del proyecto
    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)

    # Crear carpeta si no existe (extra seguro)
    os.makedirs(os.path.dirname(upload_path), exist_ok=True)

    # Guardar archivo
    archivo.save(upload_path)

    # Guardar SOLO el nombre
    empleado.foto = filename
    db.session.commit()

    flash("Foto actualizada correctamente.", "success")
    return redirect(url_for("perfil.ver_perfil"))