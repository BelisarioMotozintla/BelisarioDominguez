from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_required
from app.models.personal import MAC
from app.models import Usuario
from app.utils.db import db
from app.utils.helpers import usuarios_con_rol_requerido,roles_required  # tu decorador para control de acceso
from sqlalchemy import or_

bp = Blueprint('citas', __name__, template_folder='templates')

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

