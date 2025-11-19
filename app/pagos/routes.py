import calendar
from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from app.models.personal import Empleado, Usuario, PagoInternet  # Importar correctamente
from app.utils.helpers import roles_required,usuarios_con_rol_requerido
from app.utils.db import db
from sqlalchemy import or_
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask_login import current_user


bp = Blueprint('pagos', __name__, template_folder='templates')

#def nombre_mes(num):
#   return calendar.month_name[num].capitalize()

def nombre_mes(num):
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return meses[num - 1]

def add_months(fecha, meses):
    mes = fecha.month - 1 + meses
    año = fecha.year + mes // 12
    mes = mes % 12 + 1
    return datetime(año, mes, 1)

def meses_adeudo(fecha_fin):
    hoy = datetime.now()
    total = (hoy.year - fecha_fin.year) * 12 + (hoy.month - fecha_fin.month)
    return max(total, 0)

def siguiente_mes(fecha):
    return add_months(fecha, 1)

# Ruta para ver que vea los pagos el usuario logueado 
@bp.route("/mis_pagos")
@usuarios_con_rol_requerido
def mis_pagos():
    uid = session.get('_user_id')

    if not uid:
        flash("Inicia sesión primero.")
        return redirect(url_for('auth.login'))

    usuario = Usuario.query.get(uid)

    pagos = PagoInternet.query.filter_by(id_usuario=usuario.id_usuario)\
        .order_by(PagoInternet.fecha_pago.asc())\
        .all()

    lista = []
    ultimo_pagado = None
    total_pagado_dinero = 0

    for p in pagos:
        fecha_inicio = datetime(p.anio_inicio, p.mes_inicio, 1)
        fecha_fin = add_months(fecha_inicio, p.meses_pagados - 1)

        # guardar el último mes cubierto por todos los pagos
        if ultimo_pagado is None or fecha_fin > ultimo_pagado:
            ultimo_pagado = fecha_fin

        total_pagado_dinero += p.monto

        lista.append({
            "mes_inicio_num": p.mes_inicio,
            "anio": p.anio_inicio,
            "meses_pagados": p.meses_pagados,
            "monto": p.monto,

            # Fecha en español
            "fecha_registro": f"{p.fecha_pago.day} de {nombre_mes(p.fecha_pago.month)} de {p.fecha_pago.year}",

            # Período cubierto EN ESPAÑOL
            "rango": f"{nombre_mes(fecha_inicio.month)} {fecha_inicio.year} – {nombre_mes(fecha_fin.month)} {fecha_fin.year}",

            # Último mes cubierto
            "pagado_hasta": f"{nombre_mes(fecha_fin.month)} {fecha_fin.year}",

            # Adeudo
            "adeuda": meses_adeudo(fecha_fin)
        })
    # cálculo de adeudo general
    if ultimo_pagado:
        meses_adeuda = meses_adeudo(ultimo_pagado)
        prox = siguiente_mes(ultimo_pagado)
        proximo_mes = f"{nombre_mes(prox.month)} {prox.year}"
        total_adeudado_dinero = meses_adeuda * 25   # TU COSTO FIJO
    else:
        meses_adeuda = 0
        proximo_mes = "Sin pagos registrados"
        total_adeudado_dinero = 0

    return render_template(
        'mis_pagos.html',
        usuario=usuario,
        datos=lista,
        proximo_mes=proximo_mes,
        total_pagado_dinero=total_pagado_dinero,
        total_adeudado_dinero=total_adeudado_dinero,
        meses_adeuda=meses_adeuda
    )




# Registrar pago de usuarios
@bp.route("/registrar/<int:id_usuario>", methods=["GET", "POST"])
@roles_required(['Administrador','JefeEnfermeria','SuperUsuario'])
def registrar_pago_usuario(id_usuario):
    usuario = Usuario.query.get(id_usuario)

    if request.method == 'POST':
        mes_raw = request.form['mes_inicio']  # Ej: "2025-04"
        meses_pagados = int(request.form['meses_pagados'])
        monto = float(request.form['monto'])

        anio, mes = map(int, mes_raw.split("-"))

        pago = PagoInternet(
            mes_inicio=mes,
            anio_inicio=anio,
            meses_pagados=meses_pagados,
            monto=monto,
            id_usuario=id_usuario
        )

        db.session.add(pago)
        db.session.commit()
        return redirect(url_for('pagos.admin_panel'))

    # 🔹 Lista de meses próximos para seleccionar
    meses = []
    hoy = datetime.now()
    for i in range(0, 14):
        m = hoy + relativedelta(months=i)
        meses.append({
            "valor": m.strftime("%Y-%m"),
            "texto": m.strftime("%B %Y")
        })

    return render_template('registrar_pago.html', usuario=usuario, id_usuario=id_usuario, meses=meses)

    # GENERAR MESES FUTUROS para el select
    usuario = Usuario.query.get(id_usuario)
    meses = []
    hoy = datetime.now()
    for i in range(0, 14):
        mes = hoy + relativedelta(months=i)
        meses.append({
            "valor": mes.strftime("%Y-%m"),
            "texto": mes.strftime("%B %Y")
        })

    return render_template('registrar_pago.html', meses=meses, id_usuario=id_usuario, usuario=usuario )

# Panel de administrador
@bp.route('/admin')
@roles_required(['Administrador','JefeEnfermeria','SuperUsuario'])
def admin_panel(): 
    query = request.args.get('q')  # 🔍 Texto de búsqueda en input

    if query:
        usuarios = Usuario.query.outerjoin(Empleado).filter(
            or_(
                Usuario.usuario.ilike(f"%{query}%"),
                Empleado.telefono.ilike(f"%{query}%")
            )
        ).all()
    else:
        usuarios = Usuario.query.all()

    lista_usuarios = []

    for u in usuarios:
        pagos = PagoInternet.query.filter_by(id_usuario=u.id_usuario).all()
       
        # 📞 Si tiene empleado y teléfono
        telefono = u.empleado.telefono if u.empleado and u.empleado.telefono else "SIN TELEFONO"

        if not pagos:
            lista_usuarios.append({
                'usuario': u.usuario,
                'meses_pagados': 0,
                'ultimo_pago': "SIN REGISTROS",
                'deuda': "SIN CALCULAR",
                'telefono': telefono,
                'id_usuario': u.id_usuario
            })
            continue

        deuda, ultimo_pago, meses_pagados = calcular_adeudo(pagos)

        lista_usuarios.append({
            'usuario': u.usuario,
            'meses_pagados': meses_pagados,
            'ultimo_pago': ultimo_pago.strftime("%B %Y") if ultimo_pago else "SIN PAGOS",
            'deuda': deuda,
            'telefono': telefono,
            'id_usuario': u.id_usuario
        })
    lista_usuarios = sorted(lista_usuarios, key=lambda x: x['usuario'].lower())
    return render_template('admin_pagos.html', usuarios=lista_usuarios, query=query)


def calcular_adeudo(pagos):
    if not pagos:
        return 0, None, 0  # deuda, ultimo_pago (datetime), total_meses_pagados

    # Construir lista de meses pagados
    meses_cubiertos = []
    for p in pagos:
        for i in range(p.meses_pagados):
            mes = (p.mes_inicio + i - 1) % 12 + 1
            anio = p.anio_inicio + ((p.mes_inicio + i - 1) // 12)
            meses_cubiertos.append(datetime(anio, mes, 1))

    total_pagado = len(meses_cubiertos)
    ultimo_pago = max(meses_cubiertos)  # ⚠️ sigue siendo datetime

    # Mes actual
    hoy = datetime(datetime.now().year, datetime.now().month, 1)

    # Deuda = meses desde el último mes pagado hasta hoy
    diferencia = (hoy.year - ultimo_pago.year) * 12 + (hoy.month - ultimo_pago.month)
    deuda = max(0, diferencia)
    print(deuda)
    return deuda, ultimo_pago, total_pagado
