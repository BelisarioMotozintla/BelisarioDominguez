from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_required
from app.models.personal import MAC
from app.models import Usuario
from app.utils.db import db
from app.utils.helpers import usuarios_con_rol_requerido,roles_required  # tu decorador para control de acceso
from sqlalchemy import or_

bp = Blueprint('control_mac', __name__, template_folder='templates')

# 📌 Listar todos los dispositivos
@bp.route("/", methods=["GET"])
@roles_required(['Administrador'])
def listar_macs():
    q = request.args.get("q", "").strip()

    if q:
        macs = (
            MAC.query
            .join(Usuario, MAC.id_usuario == Usuario.id_usuario)
            .filter(
                or_(
                    MAC.mac_address.ilike(f"%{q}%"),
                    Usuario.usuario.ilike(f"%{q}%")   # buscar por nombre de usuario
                )
            )
            .all()
        )
    else:
        macs = MAC.query.all()

    return render_template("macs.html", macs=macs, q=q)

# 📌 Agregar un dispositivo
@bp.route("/agregar", methods=["GET", "POST"])
#@roles_required(['Administrador'])
@usuarios_con_rol_requerido
def agregar_mac():
    usuarios = Usuario.query.all()
    if request.method == "POST":
        user_id = request.form['usuario_id']
        usuario = Usuario.query.get(user_id)

        nuevo_mac = MAC(
            dispositivo=request.form['dispositivo'],
            mac_address=request.form['mac_address'],
            red=request.form['red'],
            observaciones=request.form['observaciones'],
            usuario=usuario
        )
        db.session.add(nuevo_mac)
        db.session.commit()
        flash("MAC registrada correctamente", "success")
        return redirect(url_for("control_mac.listar_macs"))
    return render_template("agregar_mac.html", usuarios=usuarios)

# 📌 Editar un dispositivo
@bp.route("/editar/<int:id_mac>", methods=["GET", "POST"])
@roles_required(['Administrador'])
def editar_mac(id_mac):
    mac = MAC.query.get_or_404(id_mac)
    usuarios = Usuario.query.all()

    if request.method == "POST":
        mac.dispositivo = request.form['dispositivo']
        mac.mac_address = request.form['mac_address']
        mac.red = request.form['red']
        mac.observaciones = request.form['observaciones']
        mac.id_usuario = request.form['usuario_id']

        db.session.commit()
        flash("MAC actualizada correctamente", "info")
        return redirect(url_for("control_mac.listar_macs"))

    return render_template("editar_mac.html", mac=mac, usuarios=usuarios)

# 📌 Eliminar un dispositivo
@bp.route("/eliminar/<int:id_mac>", methods=["POST"])
@roles_required(['Administrador'])
def eliminar_mac(id_mac):
    mac = MAC.query.get_or_404(id_mac)
    db.session.delete(mac)
    db.session.commit()
    flash("MAC eliminada correctamente", "danger")
    return redirect(url_for("control_mac.listar_macs"))
