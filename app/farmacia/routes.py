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
#)))))))))))))))))))))))))))))))))) medicamento
# Listar medicamentos
@bp.route('/medicamentos')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_medicamentos():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    
    # Base de la consulta ordenada
    medicamentos_query = Medicamento.query.order_by(Medicamento.principio_activo.asc())

    if query:
        # Filtro con búsqueda parcial
        medicamentos_query = medicamentos_query.filter(
            (Medicamento.clave.ilike(f'%{query}%')) |
            (Medicamento.Medicamento.principio_activo.ilike(f'%{query}%'))
        )
    
    # Paginación (ejemplo: 10 por página)
    pagination = medicamentos_query.paginate(page=page, per_page=10, error_out=False)
    medicamentos = pagination.items

    return render_template(
        'farmacia/listar_medicamentos.html', 
        medicamentos=medicamentos, 
        query=query,
        pagination=pagination
    )


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
            principio_activo=request.form.get('principio_activo').upper(),
            presentacion=request.form.get('presentacion').upper(),
            via_administracion=request.form.get('via_administracion').upper(),
            concentracion=request.form.get('concentracion'),
            unidad=request.form.get('unidad').upper(),
            # Captura de los 3 catálogos (Checkboxes)
            es_kit_basico='es_kit_basico' in request.form,
            es_180_claves='es_180_claves' in request.form,
            es_general='es_general' in request.form,
            # Captura de Stock Crítico y Óptimo
            stock_minimo=int(request.form.get('stock_minimo') or 10),
            stock_maximo=int(request.form.get('stock_maximo') or 100),
            # CPM y Movimiento
            cpm=float(request.form.get('cpm') or 0.0),
            nivel_movimiento=request.form.get('nivel_movimiento', 'Nulo')
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
        # 1. Captura y validación de Stocks
        try:
            s_min = int(request.form.get('stock_minimo') or 0)
            s_max = int(request.form.get('stock_maximo') or 0)
        except ValueError:
            flash("❌ Los valores de stock deben ser números enteros.", "danger")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        if s_min > s_max:
            flash(f"⚠️ El Stock Mínimo ({s_min}) no puede ser mayor al Máximo ({s_max}).", "warning")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        # 2. Validación de Clave Única
        nueva_clave = request.form.get('clave', '').strip().upper()
        med_existente = Medicamento.query.filter(
            Medicamento.clave == nueva_clave, 
            Medicamento.id_medicamento != id_medicamento
        ).first()
        
        if med_existente:
            flash(f"⚠️ La clave '{nueva_clave}' ya pertenece a otro medicamento.", "danger")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        try:
            # 3. Actualización con transformación a MAYÚSCULAS (.upper())
            medicamento.clave = nueva_clave
            medicamento.principio_activo = request.form.get('principio_activo', '').upper()
            medicamento.presentacion = request.form.get('presentacion', '').upper()
            medicamento.via_administracion = request.form.get('via_administracion', '').upper()
            medicamento.concentracion = request.form.get('concentracion', '').upper()
            medicamento.unidad = request.form.get('unidad', '').upper()
            
            # 4. Checkboxes (Catálogos)
            medicamento.es_kit_basico = 'es_kit_basico' in request.form
            medicamento.es_180_claves = 'es_180_claves' in request.form
            medicamento.es_general = 'es_general' in request.form
            
            # 5. Stocks y CPM
            medicamento.stock_minimo = s_min
            medicamento.stock_maximo = s_max
            medicamento.cpm = float(request.form.get('cpm') or 0.0)

            # 6. CORRECCIÓN DEL ENUM PARA POSTGRESQL
            # Convierte 'NULO' (del form) a 'Nulo' (de la DB)
            nivel_form = request.form.get('nivel_movimiento', 'Nulo')
            medicamento.nivel_movimiento = nivel_form.capitalize() 

            db.session.commit()
            flash("✅ Medicamento actualizado correctamente", "success")
            return redirect(url_for('farmacia.listar_medicamentos'))
            
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error crítico de base de datos: {str(e)}", "danger")

    return render_template('farmacia/editar_medicamento.html', medicamento=medicamento)



# Eliminar medicamento (con protección)
@bp.route('/medicamentos/eliminar/<int:id_medicamento>', methods=['POST'])
@roles_required(['Administrador'])
def eliminar_medicamento(id_medicamento):
    medicamento = Medicamento.query.get_or_404(id_medicamento)
    
    # Verificamos si tiene inventario antes de borrar para evitar error de SQL
    if medicamento.inventario_almacen or medicamento.inventario_farmacia:
        flash("❌ No se puede eliminar: El medicamento tiene existencias en inventario.", "danger")
        return redirect(url_for('farmacia.listar_medicamentos'))
        
    db.session.delete(medicamento)
    db.session.commit()
    flash("✅ Medicamento eliminado correctamente", "success")
    return redirect(url_for('farmacia.listar_medicamentos'))


#===============================================================================ENTRADA AL ALMACEN================================

@bp.route('/entradas/listar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_entradas():
    query = request.args.get('q', '').strip().upper()
    
    # Base de la consulta con JOIN para poder buscar por Clave o Principio Activo
    entradas_query = EntradaAlmacen.query.join(Medicamento)

    if query:
        entradas_query = entradas_query.filter(
            (Medicamento.clave.ilike(f'%{query}%')) |
            (Medicamento.principio_activo.ilike(f'%{query}%')) |
            (EntradaAlmacen.lote.ilike(f'%{query}%')) |
            (EntradaAlmacen.proveedor.ilike(f'%{query}%'))
        )

    # Ordenar por las más recientes primero
    entradas = entradas_query.order_by(EntradaAlmacen.fecha_entrada.desc()).all()
    
    return render_template('farmacia/entradas.html', 
                           entradas=entradas, 
                           query=query)
@bp.route('/entradas/nueva', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nueva_entrada():
    # Ordenamos por principio_activo porque nombre_comercial no está en tu modelo
    medicamentos = Medicamento.query.order_by(Medicamento.principio_activo).all()

    if request.method == 'POST':
        try:
            id_medicamento = int(request.form['id_medicamento'])
            cantidad = int(request.form['cantidad'])
            lote = request.form.get('lote', '').strip().upper()
            f_caducidad_raw = request.form.get('fecha_caducidad')
            fecha_caducidad = datetime.strptime(f_caducidad_raw, '%Y-%m-%d').date() if f_caducidad_raw else None
            
            if not lote or not fecha_caducidad:
                flash("❌ El lote y la fecha de caducidad son obligatorios para el control de inventario.", "danger")
                return redirect(url_for('farmacia.nueva_entrada'))

            # 1. Registrar la Entrada (Historial)
            nueva = EntradaAlmacen(
                id_medicamento=id_medicamento,
                cantidad=cantidad,
                lote=lote,
                fecha_caducidad=fecha_caducidad,
                fecha_entrada=datetime.utcnow(),
                proveedor=request.form.get('proveedor', '').upper(),
                observaciones=request.form.get('observaciones', '').upper(),
                id_usuario=current_user.id_usuario
            )
            db.session.add(nueva)

            # 2. ACTUALIZAR INVENTARIO POR LOTE (Punto Clave)
            # Buscamos si ya existe ESE medicamento con ESE lote en el almacén
            inventario = InventarioAlmacen.query.filter_by(
                id_medicamento=id_medicamento, 
                lote=lote
            ).first()

            if inventario:
                inventario.cantidad += cantidad
            else:
                inventario = InventarioAlmacen(
                    id_medicamento=id_medicamento, 
                    cantidad=cantidad,
                    lote=lote,
                    fecha_vencimiento=fecha_caducidad
                )
                db.session.add(inventario)

            db.session.commit()
            flash(f"✅ Entrada y Stock actualizados: {lote}", "success")
            return redirect(url_for('farmacia.listar_entradas'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al registrar entrada: {str(e)}", "danger")

    return render_template('farmacia/nueva_entrada.html', medicamentos=medicamentos)

@bp.route('/entradas/editar/<int:id_entrada>', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def editar_entrada(id_entrada):
    entrada = EntradaAlmacen.query.get_or_404(id_entrada)
    medicamentos = Medicamento.query.order_by(Medicamento.principio_activo).all()

    if request.method == 'POST':
        try:
            # 1. Guardar valores antiguos para calcular la diferencia
            lote_anterior = entrada.lote
            cantidad_anterior = entrada.cantidad
            id_med_anterior = entrada.id_medicamento

            # 2. Capturar nuevos valores
            nueva_cantidad = int(request.form['cantidad'])
            nuevo_lote = request.form.get('lote', '').strip().upper()
            f_caducidad_raw = request.form.get('fecha_caducidad')
            nueva_fecha_caducidad = datetime.strptime(f_caducidad_raw, '%Y-%m-%d').date() if f_caducidad_raw else None

            # 3. REVERTIR STOCK ANTERIOR (Limpiamos el rastro de la entrada antes del cambio)
            inv_anterior = InventarioAlmacen.query.filter_by(
                id_medicamento=id_med_anterior, 
                lote=lote_anterior
            ).first()
            
            if inv_anterior:
                inv_anterior.cantidad -= cantidad_anterior

            # 4. ACTUALIZAR REGISTRO DE ENTRADA
            entrada.id_medicamento = int(request.form['id_medicamento'])
            entrada.cantidad = nueva_cantidad
            entrada.lote = nuevo_lote
            entrada.fecha_caducidad = nueva_fecha_caducidad
            entrada.proveedor = request.form.get('proveedor', '').upper()
            entrada.observaciones = request.form.get('observaciones', '').upper()

            # 5. APLICAR NUEVO STOCK
            inv_nuevo = InventarioAlmacen.query.filter_by(
                id_medicamento=entrada.id_medicamento, 
                lote=nuevo_lote
            ).first()

            if inv_nuevo:
                inv_nuevo.cantidad += nueva_cantidad
                inv_nuevo.fecha_vencimiento = nueva_fecha_caducidad # Actualizamos caducidad por si cambió
            else:
                inv_nuevo = InventarioAlmacen(
                    id_medicamento=entrada.id_medicamento,
                    cantidad=nueva_cantidad,
                    lote=nuevo_lote,
                    fecha_vencimiento=nueva_fecha_caducidad
                )
                db.session.add(inv_nuevo)

            db.session.commit()
            flash("✅ Entrada e Inventario actualizados correctamente.", "success")
            return redirect(url_for('farmacia.listar_entradas'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al modificar: {str(e)}", "danger")

    return render_template('farmacia/editar_entrada.html', entrada=entrada, medicamentos=medicamentos)


@bp.route('/entradas/eliminar/<int:id_entrada>', methods=['POST'])
@roles_required(['Administrador'])
def eliminar_entrada(id_entrada):
    entrada = EntradaAlmacen.query.get_or_404(id_entrada)
    
    # 3. REVERTIR STOCK (Solo si hay existencia suficiente)
    inv = InventarioAlmacen.query.filter_by(id_medicamento=entrada.id_medicamento, lote=entrada.lote).first()
    
    if inv and inv.cantidad >= entrada.cantidad:
        inv.cantidad -= entrada.cantidad
        db.session.delete(entrada)
        db.session.commit()
        flash("✅ Entrada eliminada y stock revertido.", "success")
    else:
        flash("❌ No se puede eliminar: El stock de este lote ya es menor a la cantidad de esta entrada.", "danger")
        
    return redirect(url_for('farmacia.listar_entradas'))

#))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))) BUSQUEDAS  ))))))))))))))))))))))))))))))))))))))))))))))

@bp.route('/medicamentos/buscar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def buscar_medicamentos():
    q = request.args.get('q', '').strip().upper() # Buscamos en mayúsculas para coincidir
    if not q:
        return jsonify([])

    # Filtramos solo por los campos que SI existen en tu modelo
    resultados = Medicamento.query.filter(
        (Medicamento.clave.ilike(f"%{q}%")) |
        (Medicamento.principio_activo.ilike(f"%{q}%"))
    ).limit(20).all()

    # Formateamos para que Select2 muestre la info clara
    data = []
    for med in resultados:
        data.append({
            'id': med.id_medicamento,
            # Mostramos Clave y Principio Activo únicamente
            'text': f"{med.clave} | {med.principio_activo}"
        })

    return jsonify(data)



@bp.route('/buscar_lotes_almacen/<int:id_medicamento>')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def buscar_lotes_almacen(id_medicamento):
    # Buscamos en InventarioAlmacen los registros con cantidad > 0
    lotes = InventarioAlmacen.query.filter(
        InventarioAlmacen.id_medicamento == id_medicamento,
        InventarioAlmacen.cantidad > 0
    ).all()
    
    return jsonify([{
        'lote': l.lote, 
        'cantidad': l.cantidad, 
        'vencimiento': l.fecha_vencimiento.strftime('%d/%m/%Y') if l.fecha_vencimiento else 'N/A'
    } for l in lotes])



#===============================================================================MOVIMIENTO DE ALMACEN A FARMACIA================================
@bp.route('/movimientos/almacen')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_movimientos():
    # Obtener el parámetro de búsqueda
    query = request.args.get('q', '').strip().upper()
    
    # Base de la consulta con JOINs necesarios
    movimientos_query = MovimientoAlmacenFarmacia.query.join(Medicamento).join(Usuario)

    if query:
        movimientos_query = movimientos_query.filter(
            (Medicamento.nombre_comercial.ilike(f'%{query}%')) |
            (Medicamento.principio_activo.ilike(f'%{query}%')) |
            (Usuario.usuario.ilike(f'%{query}%')) |
            (MovimientoAlmacenFarmacia.observaciones.ilike(f'%{query}%'))
        )

    # Ordenar por los más recientes
    movimientos = movimientos_query.order_by(MovimientoAlmacenFarmacia.fecha_movimiento.desc()).all()
    
    return render_template('farmacia/movimientos.html', 
                           movimientos=movimientos, 
                           query=query)


@bp.route('/movimientos/nuevo_movimiento', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nuevo_movimiento():
    # 1. Obtener datos (esto siempre se ejecuta para el GET)
    medicamentos = Medicamento.query.order_by(Medicamento.principio_activo).all()

    if request.method == 'POST':
        try:
            id_medicamento = int(request.form['id_medicamento'])
            cantidad = int(request.form['cantidad'])
            lote = request.form.get('lote', '').strip().upper()
            
            # Validar existencia
            inv_almacen = InventarioAlmacen.query.filter_by(
                id_medicamento=id_medicamento, 
                lote=lote
            ).first()

            if not inv_almacen or inv_almacen.cantidad < cantidad:
                flash(f"❌ Stock insuficiente en Almacén. Disponible: {inv_almacen.cantidad if inv_almacen else 0}", "danger")
                return redirect(url_for('farmacia.nuevo_movimiento'))

            # Registrar Movimiento
            movimiento = MovimientoAlmacenFarmacia(
                id_medicamento=id_medicamento,
                cantidad=cantidad,
                lote=lote,
                fecha_vencimiento=inv_almacen.fecha_vencimiento,
                fecha_movimiento=datetime.utcnow(),
                id_usuario=current_user.id_usuario,
                observaciones=request.form.get('observaciones', '').upper()
            )
            db.session.add(movimiento)

            # Actualizar Inventarios
            inv_almacen.cantidad -= cantidad

            inv_farmacia = InventarioFarmacia.query.filter_by(id_medicamento=id_medicamento, lote=lote).first()
            if inv_farmacia:
                inv_farmacia.cantidad += cantidad
            else:
                inv_farmacia = InventarioFarmacia(
                    id_medicamento=id_medicamento,
                    cantidad=cantidad,
                    lote=lote,
                    fecha_vencimiento=inv_almacen.fecha_vencimiento
                )
                db.session.add(inv_farmacia)

            db.session.commit()
            flash(f"✅ Traslado exitoso de {cantidad} unidades.", "success")
            return redirect(url_for('farmacia.listar_movimientos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error: {str(e)}", "danger")
            # Si hay error en el POST, el código sigue hacia abajo y vuelve a cargar la página

    return render_template('farmacia/nuevo_movimiento.html', medicamentos=medicamentos)


@bp.route('/movimientos/editar/<int:id>', methods=['GET', 'POST'])
@roles_required(['Administrador']) # Sugerido solo para admin por control de stock
def editar_movimiento(id):
    movimiento = MovimientoAlmacenFarmacia.query.get_or_404(id)
    # Guardamos la cantidad original para calcular la diferencia
    cantidad_anterior = movimiento.cantidad
    medicamentos = Medicamento.query.order_by(Medicamento.principio_activo).all()

    if request.method == 'POST':
        try:
            nueva_cantidad = int(request.form['cantidad'])
            diferencia = nueva_cantidad - cantidad_anterior

            # 1. Validar stock en almacén si la cantidad aumenta
            inv_almacen = InventarioAlmacen.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()
            inv_farmacia = InventarioFarmacia.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()

            if diferencia > 0 and (not inv_almacen or inv_almacen.cantidad < diferencia):
                flash(f"❌ No hay suficiente stock extra en almacén (Faltan {diferencia - inv_almacen.cantidad} pzs)", "danger")
                return redirect(url_for('farmacia.editar_movimiento', id=id))

            # 2. Validar stock en farmacia si la cantidad disminuye (para poder devolver a almacén)
            if diferencia < 0 and (not inv_farmacia or inv_farmacia.cantidad < abs(diferencia)):
                flash("❌ No se puede reducir el movimiento: la farmacia ya no tiene suficiente stock para devolver al almacén.", "danger")
                return redirect(url_for('farmacia.editar_movimiento', id=id))

            # 3. Aplicar cambios
            inv_almacen.cantidad -= diferencia
            inv_farmacia.cantidad += diferencia
            
            movimiento.cantidad = nueva_cantidad
            movimiento.observaciones = request.form.get('observaciones', '').upper()
            
            db.session.commit()
            flash("✅ Movimiento y stocks actualizados correctamente.", "success")
            return redirect(url_for('farmacia.listar_movimientos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error: {str(e)}", "danger")

    return render_template('farmacia/editar_movimiento.html', movimiento=movimiento, medicamentos=medicamentos)

@bp.route('/movimientos/eliminar/<int:id>', methods=['POST'])
@roles_required(['Administrador'])
def eliminar_movimiento(id):
    movimiento = MovimientoAlmacenFarmacia.query.get_or_404(id)
    try:
        # Revertir stocks: Quitar de farmacia, devolver a almacén
        inv_farmacia = InventarioFarmacia.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()
        inv_almacen = InventarioAlmacen.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()

        if not inv_farmacia or inv_farmacia.cantidad < movimiento.cantidad:
            flash("❌ No se puede eliminar: el stock ya fue consumido en farmacia.", "danger")
            return redirect(url_for('farmacia.listar_movimientos'))

        inv_farmacia.cantidad -= movimiento.cantidad
        if inv_almacen:
            inv_almacen.cantidad += movimiento.cantidad
        
        db.session.delete(movimiento)
        db.session.commit()
        flash("✅ Movimiento eliminado y stock devuelto a almacén.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar: {str(e)}", "danger")
    
    return redirect(url_for('farmacia.listar_movimientos'))


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
