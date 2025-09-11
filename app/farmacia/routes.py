from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash,session
from datetime import datetime
from app import db
from app.models.farmacia import SalidaFarmaciaPaciente, Medicamento, AsignacionReceta,MovimientoAlmacenFarmacia,InventarioAlmacen,InventarioFarmacia,EntradaAlmacen,TransferenciaSaliente, TransferenciaEntrante
from app.models.personal import Usuario
from flask_login import current_user
from app.utils.helpers import roles_required

bp = Blueprint('farmacia', __name__, template_folder='templates/farmacia')

# Página principal de farmacia
@bp.route('/')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def index():
    return render_template('farmacia/index.html')


# Registrar salida
@bp.route('/salida/<int:id_medicamento>', methods=['GET', 'POST'])
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def registrar_salida(id_medicamento):
    medicamento = Medicamento.query.get_or_404(id_medicamento)
    medicos = Usuario.query.all()

    if request.method == 'POST':
        cantidad = int(request.form['cantidad'])
        id_medico = int(request.form['id_medico'])

        asignacion = AsignacionReceta.query.filter_by(
            id_medico=id_medico
        ).order_by(AsignacionReceta.id_asignacion.desc()).first()

        if not asignacion:
            flash("⚠️ El médico no tiene bloque asignado", "danger")
            return redirect(url_for('farmacia.registrar_salida', id_medicamento=id_medicamento))

        folio = asignacion.siguiente_folio()
        if not folio:
            flash("⚠️ El bloque asignado está agotado", "danger")
            return redirect(url_for('farmacia.registrar_salida', id_medicamento=id_medicamento))

        salida = SalidaFarmaciaPaciente(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            fecha_salida=datetime.utcnow(),
            id_usuario=id_medico,
            folio_receta=folio
        )

        db.session.add(salida)
        db.session.commit()

        flash(f"✅ Salida registrada con folio {folio}", "success")
        return redirect(url_for('farmacia.listar_salidas'))

    return render_template('farmacia/salida.html', medicamento=medicamento, medicos=medicos)

@bp.route('/medicamentos/buscar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def buscar_medicamentos():
    q = request.args.get('q', '').strip()  # lo que el usuario escribe
    if not q:
        return jsonify([])

    # Filtrar por clave, nombre_comercial o principio_activo
    resultados = Medicamento.query.filter(
        (Medicamento.clave.ilike(f"%{q}%")) |
        (Medicamento.nombre_comercial.ilike(f"%{q}%")) |
        (Medicamento.principio_activo.ilike(f"%{q}%"))
    ).all()

    # Formatear para Select2
    data = []
    for med in resultados:
        data.append({
            'id': med.id_medicamento,
            'text': f"{med.clave} | {med.nombre_comercial} | {med.principio_activo}"
        })

    return jsonify(data)

# Listar salidas
@bp.route('/salidas')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def listar_salidas():
    salidas = SalidaFarmaciaPaciente.query.order_by(SalidaFarmaciaPaciente.fecha_salida.desc()).all()
    return render_template('farmacia/listar_salidas.html', salidas=salidas)

@bp.route('/reporte_medicamentos')
@roles_required([ 'UsuarioAdministrativo', 'Administrador'])
def reporte_medicamentos():
    query = request.args.get('q', '')
    salidas = SalidaFarmaciaPaciente.query.join(Usuario).join(Medicamento)

    if query:
        salidas = salidas.filter(
            (Medicamento.nombre.ilike(f'%{query}%')) |
            (Usuario.usuario.ilike(f'%{query}%'))
        )

    salidas = salidas.order_by(SalidaFarmaciaPaciente.fecha_salida.desc()).all()
    return render_template('farmacia/reporte_medicamentos.html', salidas=salidas, query=query)

# Listar medicamentos
@bp.route('/medicamentos')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_medicamentos():
    query = request.args.get('q', '')
    if query:
        medicamentos = Medicamento.query.filter(
            (Medicamento.clave.ilike(f'%{query}%')) |
            (Medicamento.nombre_comercial.ilike(f'%{query}%'))
        ).all()
    else:
        medicamentos = Medicamento.query.all()
    return render_template('farmacia/listar_medicamentos.html', medicamentos=medicamentos, query=query)

# Nuevo medicamento
@bp.route('/medicamentos/nuevo', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nuevo_medicamento():
    if request.method == 'POST':
        clave = request.form['clave'].strip()
        # Verificar clave única
        if Medicamento.query.filter_by(clave=clave).first():
            flash(f"⚠️ Ya existe un medicamento con la clave {clave}", "danger")
            return redirect(url_for('farmacia.nuevo_medicamento'))

        medicamento = Medicamento(
            clave=clave,
            nombre_comercial=request.form['nombre_comercial'],
            principio_activo=request.form.get('principio_activo'),
            presentacion=request.form.get('presentacion'),
            via_administracion=request.form.get('via_administracion'),
            concentracion=request.form.get('concentracion'),
            unidad=request.form.get('unidad'),
            cpm=float(request.form.get('cpm') or 0),
            nivel_movimiento=request.form.get('nivel_movimiento')
        )
        db.session.add(medicamento)
        db.session.commit()
        flash("✅ Medicamento registrado correctamente", "success")
        return redirect(url_for('farmacia.listar_medicamentos'))

    return render_template('farmacia/nuevo_medicamento.html')

# Editar medicamento
@bp.route('/medicamentos/editar/<int:id_medicamento>', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def editar_medicamento(id_medicamento):
    medicamento = Medicamento.query.get_or_404(id_medicamento)

    if request.method == 'POST':
        nueva_clave = request.form['clave'].strip()
        # Verificar que la nueva clave no exista en otro registro
        med_existente = Medicamento.query.filter(Medicamento.clave==nueva_clave, Medicamento.id_medicamento!=id_medicamento).first()
        if med_existente:
            flash(f"⚠️ Esta clave ya pertenece a otro medicamento", "danger")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        medicamento.clave = nueva_clave
        medicamento.nombre_comercial = request.form['nombre_comercial']
        medicamento.principio_activo = request.form.get('principio_activo')
        medicamento.presentacion = request.form.get('presentacion')
        medicamento.via_administracion = request.form.get('via_administracion')
        medicamento.concentracion = request.form.get('concentracion')
        medicamento.unidad = request.form.get('unidad')
        medicamento.cpm = float(request.form.get('cpm') or 0)
        medicamento.nivel_movimiento = request.form.get('nivel_movimiento')

        db.session.commit()
        flash("✅ Medicamento actualizado correctamente", "success")
        return redirect(url_for('farmacia.listar_medicamentos'))

    return render_template('farmacia/editar_medicamento.html', medicamento=medicamento)

# Eliminar medicamento
@bp.route('/medicamentos/eliminar/<int:id_medicamento>', methods=['POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def eliminar_medicamento(id_medicamento):
    medicamento = Medicamento.query.get_or_404(id_medicamento)
    db.session.delete(medicamento)
    db.session.commit()
    flash("✅ Medicamento eliminado correctamente", "success")
    return redirect(url_for('farmacia.listar_medicamentos'))
#===============================================================================ENTRADA AL ALMACEN================================
@bp.route('/entradas/listar', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_entradas():
    entradas = EntradaAlmacen.query.order_by(EntradaAlmacen.fecha_entrada.desc()).all()
    return render_template('farmacia/entradas.html', entradas=entradas)

@bp.route('/entradas/nueva', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nueva_entrada():
    medicamentos = Medicamento.query.order_by(Medicamento.nombre_comercial).all()

    if request.method == 'POST':
        id_usuario = current_user.id_usuario  # aquí usamos current_user

        id_medicamento = int(request.form['id_medicamento'])
        cantidad = int(request.form['cantidad'])
        lote = request.form.get('lote', '')
        fecha_caducidad = request.form.get('fecha_caducidad')
        proveedor = request.form.get('proveedor', '')
        observaciones = request.form.get('observaciones', '')

        # Crear nueva entrada
        nueva = EntradaAlmacen(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            lote=lote,
            fecha_caducidad=fecha_caducidad if fecha_caducidad else None,
            fecha_entrada=datetime.utcnow(),
            proveedor=proveedor,
            observaciones=observaciones,
            id_usuario=id_usuario
        )

        db.session.add(nueva)
        db.session.commit()

        # Actualizar inventario
        inventario = InventarioAlmacen.query.filter_by(id_medicamento=id_medicamento).first()
        if inventario:
            inventario.cantidad += cantidad
        else:
            inventario = InventarioAlmacen(id_medicamento=id_medicamento, cantidad=cantidad)
            db.session.add(inventario)
        db.session.commit()

        flash(f"✅ Entrada registrada correctamente para {nueva.medicamento.nombre_comercial}", "success")
        return redirect(url_for('farmacia.listar_entradas'))

    return render_template('farmacia/nueva_entrada.html', medicamentos=medicamentos)


#===============================================================================MOVIMIENTO DE ALMACEN A FARMACIA================================
@bp.route('/movimientos/almacen')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_movimientos():
    movimientos = MovimientoAlmacenFarmacia.query.order_by(MovimientoAlmacenFarmacia.fecha_movimiento.desc()).all()
    return render_template('farmacia/movimientos.html', movimientos=movimientos)

@bp.route('/movimientos/nuevo', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nuevo_movimiento():
    medicamentos = Medicamento.query.order_by(Medicamento.nombre_comercial).all()

    if request.method == 'POST':
        id_usuario = current_user.id_usuario  # usamos current_user

        id_medicamento = int(request.form['id_medicamento'])
        cantidad = int(request.form['cantidad'])
        observaciones = request.form.get('observaciones', '')

        # 1. Crear movimiento
        movimiento = MovimientoAlmacenFarmacia(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            fecha_movimiento=datetime.utcnow(),
            observaciones=observaciones,
            id_usuario=id_usuario
        )
        db.session.add(movimiento)

        # 2. Actualizar inventarios
        inv_almacen = InventarioAlmacen.query.filter_by(id_medicamento=id_medicamento).first()
        inv_farmacia = InventarioFarmacia.query.filter_by(id_medicamento=id_medicamento).first()

        if not inv_almacen or inv_almacen.cantidad < cantidad:
            flash("⚠️ Stock insuficiente en almacén", "danger")
            return redirect(url_for('farmacia.nuevo_movimiento'))

        inv_almacen.cantidad -= cantidad
        if not inv_farmacia:
            inv_farmacia = InventarioFarmacia(id_medicamento=id_medicamento, cantidad=0)
            db.session.add(inv_farmacia)
        inv_farmacia.cantidad += cantidad

        db.session.commit()

        flash(f"✅ Movimiento registrado: {cantidad} unidades de {movimiento.medicamento.nombre_comercial}", "success")
        return redirect(url_for('farmacia.listar_movimientos'))

    return render_template('farmacia/nuevo_movimiento.html', medicamentos=medicamentos)
#=========================================================================================TRANSFERENCIA DE MEDICAMENTO A OTRA UNIDAD MEDICA =================
@bp.route('/transferencias')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_transferencias():
    salientes = TransferenciaSaliente.query.order_by(TransferenciaSaliente.fecha_transferencia.desc()).all()
    entrantes = TransferenciaEntrante.query.order_by(TransferenciaEntrante.fecha_transferencia.desc()).all()
    return render_template('farmacia/transferencias.html', salientes=salientes, entrantes=entrantes)

@bp.route('/transferencias/nueva', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nueva_transferencia():
    medicamentos = Medicamento.query.all()
    usuarios = Usuario.query.all()  # para seleccionar responsable de destino

    if request.method == 'POST':
        id_medicamento = int(request.form['id_medicamento'])
        cantidad = int(request.form['cantidad'])
        id_usuario_destino = int(request.form['id_usuario_destino'])
        observaciones = request.form.get('observaciones', '')

        # ✅ Validar inventario en farmacia origen (actual)
        inv_origen = InventarioFarmacia.query.filter_by(id_medicamento=id_medicamento).first()
        if not inv_origen or inv_origen.cantidad < cantidad:
            flash("⚠️ No hay suficiente stock en farmacia origen", "danger")
            return redirect(url_for('farmacia.nueva_transferencia'))

        # 1. Registrar transferencia saliente
        salida = TransferenciaSaliente(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            fecha_transferencia=datetime.utcnow(),
            id_usuario=session['id_usuario']  # usuario actual
        )
        db.session.add(salida)

        # 2. Actualizar inventario origen
        inv_origen.cantidad -= cantidad

        # 3. Registrar transferencia entrante
        entrada = TransferenciaEntrante(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            fecha_transferencia=datetime.utcnow(),
            id_usuario=id_usuario_destino
        )
        db.session.add(entrada)

        # 4. Actualizar inventario destino
        inv_destino = InventarioFarmacia.query.filter_by(id_medicamento=id_medicamento).first()
        if not inv_destino:
            inv_destino = InventarioFarmacia(id_medicamento=id_medicamento, cantidad=0)
            db.session.add(inv_destino)
        inv_destino.cantidad += cantidad

        db.session.commit()

        flash("✅ Transferencia registrada correctamente", "success")
        return redirect(url_for('farmacia.listar_transferencias'))

    return render_template('farmacia/nueva_transferencia.html', medicamentos=medicamentos, usuarios=usuarios)
#============================================================================================================Reporte de inventario================================

@bp.route('/inventario/reporte')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def reporte_inventario():
    medicamentos = Medicamento.query.all()

    inv_almacen = []
    inv_farmacia = []
    consolidado = []

    for med in medicamentos:
        # cantidades
        cantidad_almacen = db.session.query(InventarioAlmacen.cantidad)\
            .filter_by(id_medicamento=med.id_medicamento).scalar() or 0
        cantidad_farmacia = db.session.query(InventarioFarmacia.cantidad)\
            .filter_by(id_medicamento=med.id_medicamento).scalar() or 0
        total = cantidad_almacen + cantidad_farmacia

        # semáforo almacén
        if cantidad_almacen <= med.stock_minimo:
            estado_almacen = "danger"
        elif cantidad_almacen <= med.stock_maximo * 0.5:
            estado_almacen = "warning"
        else:
            estado_almacen = "success"

        # semáforo farmacia
        if cantidad_farmacia <= med.stock_minimo:
            estado_farmacia = "danger"
        elif cantidad_farmacia <= med.stock_maximo * 0.5:
            estado_farmacia = "warning"
        else:
            estado_farmacia = "success"

        # semáforo consolidado
        if total <= med.stock_minimo:
            estado_total = "danger"
        elif total <= med.stock_maximo * 0.5:
            estado_total = "warning"
        else:
            estado_total = "success"

        inv_almacen.append({"nombre": med.nombre_comercial, "cantidad": cantidad_almacen, "estado": estado_almacen})
        inv_farmacia.append({"nombre": med.nombre_comercial, "cantidad": cantidad_farmacia, "estado": estado_farmacia})
        consolidado.append({"nombre": med.nombre_comercial, "total": total, "estado": estado_total})

    return render_template(
        'farmacia/reporte_inventario.html',
        inv_almacen=inv_almacen,
        inv_farmacia=inv_farmacia,
        consolidado=consolidado
    )
