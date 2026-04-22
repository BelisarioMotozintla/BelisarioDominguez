from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash,session,send_file
from datetime import datetime,timedelta
import calendar
from app import db
from app.models.farmacia import SalidaFarmaciaPaciente, Medicamento, AsignacionReceta,MovimientoAlmacenFarmacia,InventarioAlmacen,InventarioFarmacia,EntradaAlmacen,TransferenciaSaliente, TransferenciaEntrante
from app.models.personal import Usuario
from flask_login import current_user
from app.utils.helpers import roles_required

from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


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
            (Medicamento.clave.ilike(f'%{query}%')) |
            (Medicamento.principio_activo.ilike(f'%{query}%')) |
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
            (Medicamento.principio_activo.ilike(f'%{query}%'))
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
        # 1. Captura y Limpieza (eliminar espacios accidentales)
        clave = request.form.get('clave', '').strip().upper()
        principio = request.form.get('principio_activo', '').strip().upper()
        presentacion = request.form.get('presentacion', '').strip().upper()

        # 2. VALIDACIÓN: Campos obligatorios vacíos o puros espacios
        if not clave or not principio or not presentacion:
            flash("❌ La clave, el principio activo y la presentación son campos obligatorios.", "warning")
            return redirect(url_for('farmacia.nuevo_medicamento'))

        # 3. VALIDACIÓN: Clave única
        if Medicamento.query.filter_by(clave=clave).first():
            flash(f"⚠️ La clave '{clave}' ya existe. Intenta con otra.", "danger")
            return redirect(url_for('farmacia.nuevo_medicamento'))

        # 4. VALIDACIÓN: Datos numéricos
        try:
            s_min = int(request.form.get('stock_minimo') or 0)
            s_max = int(request.form.get('stock_maximo') or 0)
            cpm_val = float(request.form.get('cpm') or 0.0)
        except ValueError:
            flash("❌ Los stocks deben ser números enteros y el CPM decimal.", "danger")
            return redirect(url_for('farmacia.nuevo_medicamento'))

        # 5. VALIDACIÓN: Lógica de inventario
        if s_min > s_max:
            flash(f"⚠️ Stock Mínimo ({s_min}) no puede ser mayor al Máximo ({s_max}).", "warning")
            return redirect(url_for('farmacia.nuevo_medicamento'))

        try:
            # 6. CREACIÓN DEL REGISTRO
            nuevo_med = Medicamento(
                clave=clave,
                principio_activo=principio,
                presentacion=presentacion,
                via_administracion=request.form.get('via_administracion', '').strip().upper(),
                concentracion=request.form.get('concentracion', '').strip().upper(),
                unidad=request.form.get('unidad', '').strip().upper(),
                
                # Checkboxes
                es_kit_basico='es_kit_basico' in request.form,
                es_180_claves='es_180_claves' in request.form,
                es_general='es_general' in request.form,
                
                stock_minimo=s_min,
                stock_maximo=s_max,
                cpm=cpm_val,
                nivel_movimiento=request.form.get('nivel_movimiento', 'Nulo').capitalize()
            )
            
            db.session.add(nuevo_med)
            db.session.commit()
            flash("✅ Medicamento registrado correctamente", "success")
            return redirect(url_for('farmacia.listar_medicamentos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error de base de datos: {str(e)}", "danger")
            return redirect(url_for('farmacia.nuevo_medicamento'))

    return render_template('farmacia/nuevo_medicamento.html')

# Editar medicamento
@bp.route('/medicamentos/editar/<int:id_medicamento>', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def editar_medicamento(id_medicamento):
    medicamento = Medicamento.query.get_or_404(id_medicamento)

    if request.method == 'POST':
        # 1. Captura y Limpieza inicial
        nueva_clave = request.form.get('clave', '').strip().upper()
        principio = request.form.get('principio_activo', '').strip().upper()
        presentacion = request.form.get('presentacion', '').strip().upper()

        # --- VALIDACIÓN DE CAMPOS VACÍOS ---
        if not nueva_clave or not principio or not presentacion:
            flash("❌ La clave, el principio activo y la presentación no pueden estar vacíos.", "warning")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        # 2. Validación de Stocks (Números)
        try:
            s_min = int(request.form.get('stock_minimo') or 0)
            s_max = int(request.form.get('stock_maximo') or 0)
            cpm_val = float(request.form.get('cpm') or 0.0)
        except ValueError:
            flash("❌ Los valores de stock y CPM deben ser numéricos.", "danger")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        if s_min > s_max:
            flash(f"⚠️ El Stock Mínimo ({s_min}) no puede ser mayor al Máximo ({s_max}).", "warning")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        # 3. Validación de Clave Única
        med_existente = Medicamento.query.filter(
            Medicamento.clave == nueva_clave, 
            Medicamento.id_medicamento != id_medicamento
        ).first()
        
        if med_existente:
            flash(f"⚠️ La clave '{nueva_clave}' ya pertenece a otro medicamento.", "danger")
            return redirect(url_for('farmacia.editar_medicamento', id_medicamento=id_medicamento))

        try:
            # 4. Actualización
            medicamento.clave = nueva_clave
            medicamento.principio_activo = principio
            medicamento.presentacion = presentacion
            medicamento.via_administracion = request.form.get('via_administracion', '').strip().upper()
            medicamento.concentracion = request.form.get('concentracion', '').strip().upper()
            medicamento.unidad = request.form.get('unidad', '').strip().upper()
            
            medicamento.es_kit_basico = 'es_kit_basico' in request.form
            medicamento.es_180_claves = 'es_180_claves' in request.form
            medicamento.es_general = 'es_general' in request.form
            
            medicamento.stock_minimo = s_min
            medicamento.stock_maximo = s_max
            medicamento.cpm = cpm_val

            # CORRECCIÓN DEL ENUM PARA POSTGRESQL
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
    entradas = entradas_query.order_by(EntradaAlmacen.fecha_entrada.desc()).limit(10).all()

    
    return render_template('farmacia/entradas.html', 
                           entradas=entradas, 
                           query=query)



@bp.route('/descargar_oc99')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def descargar_oc99():
    try:
        # 1. CAPTURAR DATOS DEL FILTRO (Vía request.args desde JS/SweetAlert2)
        ahora = datetime.now()
        anio = request.args.get('anio', ahora.year, type=int)
        mes = request.args.get('mes', ahora.month, type=int)

        # 2. CALCULAR DÍAS DEL MES SELECCIONADO
        dias_mes = calendar.monthrange(anio, mes)[1]

        # 3. OBTENER MEDICAMENTOS ÚNICOS
        medicamentos = db.session.query(Medicamento).order_by(Medicamento.clave).all()

        # 4. OBTENER ENTRADAS FILTRADAS POR MES Y AÑO
        entradas = db.session.query(EntradaAlmacen).join(Medicamento).filter(
            db.extract('year', EntradaAlmacen.fecha_entrada) == anio,
            db.extract('month', EntradaAlmacen.fecha_entrada) == mes
        ).all()

        # 5. CREAR MATRIZ DE DATOS
        matriz = {}
        for med in medicamentos:
            # CONCATENAMOS: "PRINCIPIO ACTIVO - PRESENTACIÓN"
            # .strip() elimina espacios accidentales y .upper() estandariza
            nombre_full = f"{med.principio_activo or ''} - {med.presentacion or ''}".strip().upper()
            
            matriz[med.id_medicamento] = {
                'clave': med.clave,
                'nombre_completo': nombre_full,
                'dias': {d: 0 for d in range(1, dias_mes + 1)}
            }

        # Llenar la matriz con las cantidades de las entradas
        for e in entradas:
            dia = e.fecha_entrada.day
            if e.id_medicamento in matriz:
                matriz[e.id_medicamento]['dias'][dia] += e.cantidad

        # 6. CONSTRUIR EL ARCHIVO EXCEL
        wb = Workbook()
        ws = wb.active
        ws.title = f"OC99_{mes}_{anio}"

        # ENCABEZADOS
        headers = ["CLAVE", "MEDICAMENTO (PRINCIPIO - PRESENTACIÓN)"] + [str(d) for d in range(1, dias_mes + 1)]
        ws.append(headers)

        # Estilo para los encabezados (Verde, Negrita, Texto Blanco)
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="28A745", end_color="28A745", fill_type="solid")
        center_alignment = Alignment(horizontal="center", vertical="center")

        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_alignment

        # LLENADO DE FILAS
        for med in matriz.values():
            fila = [
                med['clave'],
                med['nombre_completo']
            ] + [med['dias'][d] for d in range(1, dias_mes + 1)]
            ws.append(fila)

        # 7. AJUSTES FINALES DE DISEÑO
        ws.column_dimensions['A'].width = 15  # Clave
        ws.column_dimensions['B'].width = 70  # Nombre concatenado (más ancho)
        
        # Ajustar ancho de las columnas de los días (columnas C en adelante)
        for col_idx in range(3, 3 + dias_mes):
            col_letter = ws.cell(row=1, column=col_idx).column_letter
            ws.column_dimensions[col_letter].width = 4
            # Alinear números de los días al centro
            for cell in ws[col_letter]:
                cell.alignment = center_alignment

        # 8. PREPARAR DESCARGA
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        nombre_archivo = f"REPORTE_OC99_{mes:02d}_{anio}.xlsx"

        return send_file(
            output,
            download_name=nombre_archivo,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        flash(f"❌ Error al generar el reporte: {str(e)}", "danger")
        return redirect(url_for('farmacia.reporte_inventario'))



@bp.route('/descargar_entradas')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def descargar_entradas():
    # 1. Capturar parámetros dinámicos
    from datetime import datetime
    ahora = datetime.now()
    anio = request.args.get('anio', ahora.year, type=int)
    mes = request.args.get('mes', ahora.month, type=int)

    # 2. Consulta a la base de datos
    entradas = db.session.query(
        Medicamento.clave,
        Medicamento.principio_activo,
        Medicamento.presentacion,  # Agregado para concatenar
        EntradaAlmacen.lote,
        EntradaAlmacen.cantidad,
        EntradaAlmacen.fecha_caducidad
    ).join(Medicamento).filter(
        db.extract('year', EntradaAlmacen.fecha_entrada) == anio,
        db.extract('month', EntradaAlmacen.fecha_entrada) == mes
    ).all()

    # 3. Crear el Excel
    wb = Workbook()
    ws = wb.active
    ws.title = f"Entradas_{mes}_{anio}"

    # Encabezados con estilo
    headers = ["CLAVE", "MEDICAMENTO (PRINCIPIO - PRESENTACIÓN)", "LOTE", "CANTIDAD", "FECHA DE CADUCIDAD"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0D6EFD", end_color="0D6EFD", fill_type="solid") # Azul para Entradas
    
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # 4. Llenar los datos
    for e in entradas:
        # Concatenamos igual que en el OC99
        nombre_completo = f"{e.principio_activo or ''} - {e.presentacion or ''}".strip().upper()
        
        ws.append([
            e.clave,
            nombre_completo,
            e.lote,
            e.cantidad,
            e.fecha_caducidad.strftime('%d/%m/%Y') if e.fecha_caducidad else "N/A"
        ])

    # 5. Ajustar anchos
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 60 # Columna concatenada
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 20

    # 6. Preparar descarga
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    nombre_archivo = f"ENTRADAS_DETALLADO_{mes:02d}_{anio}.xlsx"

    return send_file(
        output,
        download_name=nombre_archivo,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@bp.route('/entradas/nueva', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nueva_entrada():
    if request.method == 'GET':
        return render_template('farmacia/nueva_entrada.html')

    try:
        # 1. Parámetros de Cabecera
        destino = request.form.get('destino') # 'almacen' o 'farmacia'
        proveedor = request.form.get('proveedor', '').strip().upper()
        obs_general = request.form.get('observaciones_general', '').strip().upper()

        # 2. Listas del Formulario (Multi-fila)
        ids_medicamentos = request.form.getlist('id_medicamento[]')
        lotes = request.form.getlist('lote[]')
        cantidades = request.form.getlist('cantidad[]')
        fechas_cad = request.form.getlist('fecha_caducidad[]')
        notas_items = request.form.getlist('notas_item[]')

        if not ids_medicamentos:
            flash("❌ No hay datos para registrar.", "warning")
            return redirect(url_for('farmacia.nueva_entrada'))

        # 3. Procesamiento en Bloque
        for i in range(len(ids_medicamentos)):
            # Conversión y limpieza de datos por fila
            id_med = int(ids_medicamentos[i])
            cant = int(cantidades[i])
            lote_actual = lotes[i].strip().upper()
            f_cad = datetime.strptime(fechas_cad[i], '%Y-%m-%d').date()
            nota_actual = f"{obs_general} | {notas_items[i]}".strip(" | ").upper()

            # A. Historial Global (Siempre en EntradaAlmacen como log de auditoría)
            nueva_entrada_log = EntradaAlmacen(
                id_medicamento=id_med,
                cantidad=cant,
                lote=lote_actual,
                fecha_caducidad=f_cad,
                fecha_entrada=datetime.utcnow(),
                proveedor=proveedor,
                observaciones=f"ENTRADA DIRECTA A {destino.upper()} - {nota_actual}",
                id_usuario=current_user.id_usuario
            )
            db.session.add(nueva_entrada_log)

            # B. Actualización de Stock según Destino Seleccionado
            if destino == 'farmacia':
                modelo_inventario = InventarioFarmacia
            else:
                modelo_inventario = InventarioAlmacen

            # Buscar si el lote ya existe en el destino seleccionado
            stock_item = modelo_inventario.query.filter_by(
                id_medicamento=id_med, 
                lote=lote_actual
            ).first()

            if stock_item:
                stock_item.cantidad += cant
            else:
                nuevo_stock = modelo_inventario(
                    id_medicamento=id_med,
                    cantidad=cant,
                    lote=lote_actual,
                    fecha_vencimiento=f_cad
                )
                db.session.add(nuevo_stock)

        # 4. Confirmación única de la transacción
        db.session.commit()
        flash(f"✅ Éxito: {len(ids_medicamentos)} registros guardados en {destino.upper()}.", "success")
        return redirect(url_for('farmacia.listar_entradas'))

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error en el proceso masivo: {str(e)}", "danger")
        return redirect(url_for('farmacia.nueva_entrada'))

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
            (Medicamento.clave.ilike(f'%{query}%')) |
            (Medicamento.principio_activo.ilike(f'%{query}%')) |
            (Usuario.usuario.ilike(f'%{query}%')) |
            (MovimientoAlmacenFarmacia.observaciones.ilike(f'%{query}%'))
        )

    # Ordenar por los más recientes
    movimientos = movimientos_query.order_by(MovimientoAlmacenFarmacia.fecha_movimiento.desc()).limit(10).all()

        
    return render_template('farmacia/movimientos.html', 
                           movimientos=movimientos, 
                           query=query)


@bp.route('/movimientos/nuevo_movimiento', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nuevo_movimiento():
    if request.method == 'GET':
        return render_template('farmacia/nuevo_movimiento.html')

    if request.method == 'POST':
        try:
            # 1. Obtener datos de cabecera
            tipo_movimiento = request.form.get('tipo_movimiento')
            destino_externo = request.form.get('destino_externo', '').strip().upper()
            obs_general = request.form.get('obs_general', '').strip().upper()
            
            ids_medicamentos = request.form.getlist('id_medicamento[]')
            lotes = request.form.getlist('lote[]')
            cantidades = request.form.getlist('cantidad[]')

            if not ids_medicamentos:
                flash("❌ No se seleccionaron productos.", "warning")
                return redirect(url_for('farmacia.nuevo_movimiento'))

            # Construir observación detallada
            obs_final = f"{tipo_movimiento}: {obs_general}"
            if destino_externo:
                obs_final += f" - DESTINO: {destino_externo}"

            # 2. Procesar cada fila
            for i in range(len(ids_medicamentos)):
                id_med = int(ids_medicamentos[i])
                lote_actual = lotes[i].strip().upper()
                cant_a_trasladar = int(cantidades[i])
                
                inv_almacen = InventarioAlmacen.query.filter_by(
                    id_medicamento=id_med, 
                    lote=lote_actual
                ).first()

                if not inv_almacen or inv_almacen.cantidad < cant_a_trasladar:
                    nombre_med = inv_almacen.medicamento.principio_activo if inv_almacen else f"ID {id_med}"
                    raise Exception(f"Stock insuficiente para {nombre_med} (Lote: {lote_actual}).")

                # A. Historial
                movimiento = MovimientoAlmacenFarmacia(
                    id_medicamento=id_med,
                    cantidad=cant_a_trasladar,
                    lote=lote_actual,
                    fecha_vencimiento=inv_almacen.fecha_vencimiento,
                    fecha_movimiento=datetime.utcnow(),
                    id_usuario=current_user.id_usuario,
                    observaciones=obs_final.strip()
                )
                db.session.add(movimiento)

                # B. Restar de Almacén
                inv_almacen.cantidad -= cant_a_trasladar

                # C. Sumar a Farmacia (Solo si es traslado interno)
                if tipo_movimiento == 'TRASLADO_FARMACIA':
                    inv_farmacia = InventarioFarmacia.query.filter_by(
                        id_medicamento=id_med, 
                        lote=lote_actual
                    ).first()

                    if inv_farmacia:
                        inv_farmacia.cantidad += cant_a_trasladar
                    else:
                        inv_farmacia = InventarioFarmacia(
                            id_medicamento=id_med,
                            cantidad=cant_a_trasladar,
                            lote=lote_actual,
                            fecha_vencimiento=inv_almacen.fecha_vencimiento
                        )
                        db.session.add(inv_farmacia)

            db.session.commit()
            flash(f"✅ Operación {tipo_movimiento} procesada correctamente.", "success")
            return redirect(url_for('farmacia.listar_movimientos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error: {str(e)}", "danger")
            return redirect(url_for('farmacia.nuevo_movimiento'))

    return render_template('farmacia/nuevo_movimiento.html')

@bp.route('/movimientos/editar/<int:id>', methods=['GET', 'POST'])
@roles_required(['Administrador'])
def editar_movimiento(id):
    movimiento = MovimientoAlmacenFarmacia.query.get_or_404(id)
    cantidad_anterior = movimiento.cantidad
    medicamentos = Medicamento.query.order_by(Medicamento.principio_activo).all()

    if request.method == 'POST':
        try:
            nueva_cantidad = int(request.form['cantidad'])
            diferencia = nueva_cantidad - cantidad_anterior
            
            # Detectar el tipo de movimiento desde las observaciones o un campo tipo si lo agregaste
            # Aquí usamos una lógica simple: si existe en farmacia y la obs dice TRASLADO, es un traslado.
            es_traslado = "TRASLADO_FARMACIA" in movimiento.observaciones

            # 1. Buscar registros de inventario
            inv_almacen = InventarioAlmacen.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()
            inv_farmacia = InventarioFarmacia.query.filter_by(id_medicamento=movimiento.id_medicamento, lote=movimiento.lote).first()

            # --- VALIDACIONES ---
            
            # A. Si la cantidad AUMENTA: Validar que el Almacén tenga el extra
            if diferencia > 0:
                if not inv_almacen or inv_almacen.cantidad < diferencia:
                    stock_disp = inv_almacen.cantidad if inv_almacen else 0
                    raise Exception(f"Stock insuficiente en almacén. Disponible extra: {stock_disp}")

            # B. Si la cantidad DISMINUYE y es TRASLADO: Validar que Farmacia tenga para devolver
            if diferencia < 0 and es_traslado:
                if not inv_farmacia or inv_farmacia.cantidad < abs(diferencia):
                    raise Exception("No se puede reducir: Farmacia ya consumió/vendió parte de este lote.")

            # --- APLICAR CAMBIOS ---

            # 1. Afectar Almacén (Siempre se afecta)
            if inv_almacen:
                inv_almacen.cantidad -= diferencia
            else:
                # Caso extremo: el registro de almacén desapareció (se borró el lote)
                raise Exception("El registro de lote en almacén ya no existe. No se puede editar.")

            # 2. Afectar Farmacia (SOLO si el movimiento original fue un traslado)
            if es_traslado:
                if inv_farmacia:
                    inv_farmacia.cantidad += diferencia
                else:
                    # Si no existe en farmacia pero es traslado, lo creamos (caso raro)
                    inv_farmacia = InventarioFarmacia(
                        id_medicamento=movimiento.id_medicamento,
                        cantidad=nueva_cantidad,
                        lote=movimiento.lote,
                        fecha_vencimiento=movimiento.fecha_vencimiento
                    )
                    db.session.add(inv_farmacia)

            # 3. Actualizar el registro del movimiento
            movimiento.cantidad = nueva_cantidad
            movimiento.observaciones = request.form.get('observaciones', '').upper()
            
            db.session.commit()
            flash("✅ Movimiento y stocks actualizados correctamente.", "success")
            return redirect(url_for('farmacia.listar_movimientos'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error: {str(e)}", "danger")
            return redirect(url_for('farmacia.editar_movimiento', id=id))

    return render_template('farmacia/editar_movimiento.html', movimiento=movimiento, medicamentos=medicamentos)

@bp.route('/movimientos/eliminar/<int:id>', methods=['POST'])
@roles_required(['Administrador'])
def eliminar_movimiento(id):
    movimiento = MovimientoAlmacenFarmacia.query.get_or_404(id)
    try:
        # 1. Identificar si el movimiento afectó a la farmacia
        # Basado en la etiqueta que pusimos en el proceso masivo
        es_traslado = "TRASLADO_FARMACIA" in (movimiento.observaciones or "")

        inv_almacen = InventarioAlmacen.query.filter_by(
            id_medicamento=movimiento.id_medicamento, 
            lote=movimiento.lote
        ).first()

        # 2. Lógica de reversión para Traslados a Farmacia
        if es_traslado:
            inv_farmacia = InventarioFarmacia.query.filter_by(
                id_medicamento=movimiento.id_medicamento, 
                lote=movimiento.lote
            ).first()

            # Validar si la farmacia tiene suficiente para devolver
            if not inv_farmacia or inv_farmacia.cantidad < movimiento.cantidad:
                raise Exception("No se puede eliminar: el stock ya fue consumido o no existe en farmacia.")
            
            # Restamos de farmacia
            inv_farmacia.cantidad -= movimiento.cantidad
        
        # 3. Devolver siempre al Almacén (independientemente del tipo de movimiento)
        if inv_almacen:
            inv_almacen.cantidad += movimiento.cantidad
        else:
            # Si por alguna razón el registro del lote desapareció de almacén, lo recreamos
            nuevo_inv_almacen = InventarioAlmacen(
                id_medicamento=movimiento.id_medicamento,
                cantidad=movimiento.cantidad,
                lote=movimiento.lote,
                fecha_vencimiento=movimiento.fecha_vencimiento
            )
            db.session.add(nuevo_inv_almacen)

        # 4. Borrar el registro del historial
        db.session.delete(movimiento)
        db.session.commit()
        
        mensaje = "Movimiento anulado. El stock ha retornado al Almacén"
        if es_traslado: mensaje += " y se descontó de Farmacia."
        else: mensaje += " (Baja/Transferencia cancelada)."
        
        flash(f"✅ {mensaje}", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al eliminar: {str(e)}", "danger")
    
    return redirect(url_for('farmacia.listar_movimientos'))
@bp.route('/descargar_traspasos_oc99')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def descargar_traspasos_oc99():
    from datetime import datetime
    import calendar
    
    ahora = datetime.now()
    anio = request.args.get('anio', ahora.year, type=int)
    mes = request.args.get('mes', ahora.month, type=int)
    dias_mes = calendar.monthrange(anio, mes)[1]

    # 1. Obtener datos
    medicamentos = db.session.query(Medicamento).order_by(Medicamento.clave).all()
    traspasos = db.session.query(MovimientoAlmacenFarmacia).filter(
        db.extract('year', MovimientoAlmacenFarmacia.fecha_movimiento) == anio,
        db.extract('month', MovimientoAlmacenFarmacia.fecha_movimiento) == mes
    ).all()

    # 2. Matriz de datos y Totales por día
    matriz = {}
    totales_piezas_dia = {d: 0 for d in range(1, dias_mes + 1)}
    claves_por_dia = {d: set() for d in range(1, dias_mes + 1)}

    for med in medicamentos:
        nombre_completo = f"{med.principio_activo or ''} - {med.presentacion or ''}".strip().upper()
        matriz[med.id_medicamento] = {
            'clave': med.clave,
            'nombre': nombre_completo,
            'dias': {d: 0 for d in range(1, dias_mes + 1)}
        }

    for t in traspasos:
        dia = t.fecha_movimiento.day
        if t.id_medicamento in matriz:
            matriz[t.id_medicamento]['dias'][dia] += t.cantidad
            totales_piezas_dia[dia] += t.cantidad
            if t.cantidad > 0:
                claves_por_dia[dia].add(t.id_medicamento)

    # 3. Crear Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "OC99 Traspasos"

    # --- CUADRO DE RESUMEN SUPERIOR (Como en la imagen) ---
    font_bold = Font(bold=True)
    fill_resumen = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    # Fila de TOTAL CLAVES
    fila_claves = ["TOTAL CLAVES:", ""] + [len(claves_por_dia[d]) for d in range(1, dias_mes + 1)]
    ws.append(fila_claves)
    
    # Fila de TOTAL PIEZAS
    fila_piezas = ["TOTAL PIEZAS:", ""] + [totales_piezas_dia[d] for d in range(1, dias_mes + 1)]
    ws.append(fila_piezas)

    # Estilo para el resumen
    for row in ws.iter_rows(min_row=1, max_row=2):
        for cell in row:
            cell.font = font_bold
            cell.fill = fill_resumen
            cell.alignment = Alignment(horizontal="center")

    ws.append([]) # Espacio en blanco

    # 4. ENCABEZADOS DE LA TABLA
    headers = ["CLAVE", "MEDICAMENTO"] + [str(d) for d in range(1, dias_mes + 1)]
    ws.append(headers)
    
    header_fill = PatternFill(start_color="FD7E14", end_color="FD7E14", fill_type="solid") # Naranja
    for cell in ws[4]: # La fila 4 es ahora el encabezado
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # 5. DATOS DE MEDICAMENTOS
    for med in matriz.values():
        fila = [med['clave'], med['nombre']] + [med['dias'][d] for d in range(1, dias_mes + 1)]
        ws.append(fila)

    # 6. AJUSTES FINALES
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 60
    
    # Ajustar ancho de columnas de días
    for col_idx in range(3, 3 + dias_mes):
        ws.column_dimensions[ws.cell(row=4, column=col_idx).column_letter].width = 5

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(output, download_name=f"OC99_TRASPASOS_{mes:02d}_{anio}.xlsx", as_attachment=True)


#=========================================================================================TRANSFERENCIA DE MEDICAMENTO A OTRA UNIDAD MEDICA =================
@bp.route('/transferencias')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_transferencias():
    # 1. Mantenemos las tablas viejas por si tienes historial que no quieres perder
    salientes_viejas = TransferenciaSaliente.query.order_by(TransferenciaSaliente.fecha_transferencia.desc()).all()
    entrantes_viejas = TransferenciaEntrante.query.order_by(TransferenciaEntrante.fecha_transferencia.desc()).all()

    # 2. Obtenemos las "Nuevas Transferencias" y "Bajas" desde la tabla de movimientos
    # Filtramos por las palabras clave que pusimos en el proceso masivo
    movimientos_especiales = MovimientoAlmacenFarmacia.query.filter(
        (MovimientoAlmacenFarmacia.observaciones.like('%TRANSFERENCIA_EXTERNA%')) |
        (MovimientoAlmacenFarmacia.observaciones.like('%BAJA_CADUCIDAD%')) |
        (MovimientoAlmacenFarmacia.observaciones.like('%BAJA_MERMA%'))
    ).order_by(MovimientoAlmacenFarmacia.fecha_movimiento.desc()).all()

    return render_template(
        'farmacia/transferencias.html', 
        salientes=salientes_viejas, 
        entrantes=entrantes_viejas,
        especiales=movimientos_especiales # Estos son los nuevos
    )


#============================================================================================================Reporte de inventario================================
from datetime import datetime, timedelta

@bp.route('/inventario/reporte')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def reporte_inventario():
    # 1. Traemos medicamentos con sus relaciones (Optimizado)
    medicamentos = Medicamento.query.options(
        db.joinedload(Medicamento.inventario_almacen),
        db.joinedload(Medicamento.inventario_farmacia)
    ).all()
    
    reporte = []
    hoy = datetime.utcnow().date()
    limite_vencimiento = hoy + timedelta(days=90) # Alerta 3 meses antes

    for med in medicamentos:
        # --- PROCESAR ALMACÉN ---
        lotes_alm = []
        cant_alm = 0
        for i in med.inventario_almacen:
            if i.cantidad > 0:
                cant_alm += i.cantidad
                lotes_alm.append({
                    "lote": i.lote, 
                    "cant": i.cantidad, 
                    "vence": i.fecha_vencimiento.strftime('%d/%m/%Y') if i.fecha_vencimiento else 'N/A'
                })

        # --- PROCESAR FARMACIA ---
        lotes_far = []
        cant_far = 0
        for i in med.inventario_farmacia:
            if i.cantidad > 0:
                cant_far += i.cantidad
                lotes_far.append({
                    "lote": i.lote, 
                    "cant": i.cantidad, 
                    "vence": i.fecha_vencimiento.strftime('%d/%m/%Y') if i.fecha_vencimiento else 'N/A'
                })

        # --- CÁLCULOS GENERALES ---
        total = cant_alm + cant_far
        
        # Unimos todos los lotes en un solo texto para que el buscador de la tabla los encuentre
        texto_busqueda_lotes = " ".join([l['lote'] for l in lotes_alm] + [l['lote'] for l in lotes_far])
        
        # Revisar si algún lote (de cualquier lado) vence pronto
        vence_pronto = any(
            inv.fecha_vencimiento and inv.fecha_vencimiento <= limite_vencimiento 
            for inv in (med.inventario_almacen + med.inventario_farmacia) if inv.cantidad > 0
        )

        # Semáforo (Tu lógica original)
        def calcular_color(cantidad, min_s, max_s):
            if cantidad <= min_s: return "danger"
            if cantidad <= (max_s * 0.5): return "warning"
            return "success"

        # 2. ARMAR EL DICCIONARIO PARA EL HTML
        reporte.append({
            "clave": med.clave,
            "nombre": med.principio_activo,
            "presentacion": med.presentacion,
            "lotes_busqueda": texto_busqueda_lotes,
            "vence_pronto": vence_pronto,
            "lotes_almacen": lotes_alm,   # <--- Importante para el Modal
            "lotes_farmacia": lotes_far,  # <--- Importante para el Modal
            "almacen": {"cant": cant_alm, "color": calcular_color(cant_alm, med.stock_minimo, med.stock_maximo)},
            "farmacia": {"cant": cant_far, "color": calcular_color(cant_far, med.stock_minimo, med.stock_maximo)},
            "total": {"cant": total, "color": calcular_color(total, med.stock_minimo, med.stock_maximo)}
        })

    return render_template('farmacia/reporte_inventario.html', reporte=reporte)


