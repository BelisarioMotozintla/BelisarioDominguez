# app/recetas/routes.py
from flask import Blueprint, request, render_template, redirect, url_for, flash
from app import db
from datetime import datetime
from app.models import BloqueReceta, AsignacionReceta, Usuario,Roles, RecetaMedica,SalidaFarmaciaPaciente,InventarioFarmacia,Medicamento,DetalleReceta,Diagnostico
from app.models.medicos import NotaConsultaExterna
from app.models.archivo_clinico import  Paciente
from app.utils.helpers import roles_required
from flask_login import current_user


bp = Blueprint('recetas', __name__, template_folder='templates/recetas')


# Registrar bloque
@bp.route('/nuevo_bloque', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def nuevo_bloque():
    if request.method == 'POST':
        folio_inicio = int(request.form['folio_inicio'])
        folio_fin = int(request.form['folio_fin'])
        bloque = BloqueReceta(
            folio_inicio=folio_inicio,
            folio_fin=folio_fin,
            creado_por=current_user.id_usuario  # registrar el usuario que crea
        )
        db.session.add(bloque)
        db.session.commit()
        flash("Bloque registrado correctamente", "success")
        return redirect(url_for('recetas.nuevo_bloque'))
    return render_template('recetas/nuevo_bloque.html')

# Asignar bloque a un médico
@bp.route('/asignar', methods=['GET', 'POST'])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def asignar():
    bloques = BloqueReceta.query.filter_by(asignado=False).all()
    medicos = Usuario.query.join(Roles).filter(Roles.nombre_rol == 'USUARIOMEDICO').all()

    if request.method == 'POST':
        id_bloque = int(request.form['id_bloque'])
        id_medico = int(request.form['id_medico'])

        bloque = BloqueReceta.query.get_or_404(id_bloque)

        asignacion = AsignacionReceta(
            id_bloque=id_bloque,
            id_medico=id_medico,
            id_asignador=current_user.id_usuario,  # usuario que asigna
            folio_actual=bloque.folio_inicio
        )
        bloque.asignado = True

        db.session.add(asignacion)
        db.session.commit()

        flash("✅ Bloque asignado correctamente", "success")
        return redirect(url_for('recetas.asignar'))

    return render_template('recetas/asignar.html', bloques=bloques, medicos=medicos)

@bp.route("/recetas", methods=["GET"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def lista_recetas():
    # Traer todas las recetas ordenadas por fecha descendente
    recetas = RecetaMedica.query.order_by(RecetaMedica.fecha_emision.desc()).all()
    return render_template("recetas/lista_recetas.html", recetas=recetas)
#=================================================================================== SALIDA DE RECETAS ================================

@bp.route('/salidas/listar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_salidas():
    # Capturar búsqueda (folio, paciente, etc.)
    query = request.args.get('q', '').strip()
    
    # Base de la consulta usando los modelos reales
    # Nota: Asegúrate de que las relaciones estén definidas en tus modelos
    salidas_query = SalidaFarmaciaPaciente.query\
        .join(Medicamento)\
        .outerjoin(RecetaMedica)\
        .outerjoin(Paciente)

    if query:
        # Buscamos ignorando mayúsculas/minúsculas
        search = f"%{query}%"
        salidas_query = salidas_query.filter(
            (RecetaMedica.folio.ilike(search)) |
            (Paciente.nombre.ilike(search)) |
            (Medicamento.principio_activo.ilike(search)) |
            (SalidaFarmaciaPaciente.lote.ilike(search))
        )

    # Ordenar por fecha de salida descendente
    salidas = salidas_query.order_by(SalidaFarmaciaPaciente.fecha_salida.desc()).all()
    
    return render_template('recetas/listar_salidas.html', 
                           salidas=salidas, 
                           query=query)



@bp.route("/recetas/crear/<int:id_nota>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO','UsuarioPasante','Administrador'])
def crear_receta(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    consulta = nota.consulta  
    paciente = consulta.paciente  
    id_medico = current_user.id_usuario

    # Medicamentos con stock en farmacia (usando Clave y Principio Activo)
    medicamentos_db = db.session.query(Medicamento, InventarioFarmacia).outerjoin(
        InventarioFarmacia, InventarioFarmacia.id_medicamento == Medicamento.id_medicamento
    ).all()

    medicamentos = [
        {
            "id": m.id_medicamento,
            "descripcion": f"{m.clave} - {m.principio_activo} ({m.presentacion})",
            "existencia": inv.cantidad if inv else 0
        } for m, inv in medicamentos_db
    ]

    asignacion = AsignacionReceta.query.filter_by(id_medico=id_medico)\
                                      .order_by(AsignacionReceta.id_asignacion.desc()).first()

    if not asignacion:
        flash("⚠️ No tienes un bloque de recetas asignado. Contacta al administrador.", "danger")
        return redirect(url_for('medicos.ver_nota', id_nota=id_nota))

    if request.method == "POST":
        folio = asignacion.siguiente_folio()
        if not folio:
            flash("⚠️ Tu bloque de folios se ha agotado.", "danger")
            return redirect(request.url)

        try:
            nueva_receta = RecetaMedica(
                id_asignacion=asignacion.id_asignacion,
                id_paciente=paciente.id_paciente,
                id_usuario=id_medico,
                folio=folio,
                nota_id=nota.id_nota,
                diagnostico_id=request.form.get("diagnostico_id")
            )
            db.session.add(nueva_receta)
            db.session.flush()

            for i in range(1, 4):
                id_med = request.form.get(f"med_{i}")
                cant = request.form.get(f"cant_{i}")
                if id_med and cant:
                    detalle = DetalleReceta(
                        id_receta=nueva_receta.id_receta,
                        id_medicamento=int(id_med),
                        cantidad=int(cant),
                        dosis=request.form.get(f"dosis_{i}").upper(),
                        indicaciones=request.form.get(f"indicaciones_{i}").upper()
                    )
                    db.session.add(detalle)

            db.session.commit()
            flash(f"✅ Receta folio {folio} creada exitosamente.", "success")
            return redirect(url_for("recetas.detalle_receta", id_receta=nueva_receta.id_receta))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al crear receta: {str(e)}", "danger")

    return render_template("recetas/crear_receta.html", 
                           nota=nota, consulta=consulta, paciente=paciente,
                           medicamentos=medicamentos, 
                           diagnosticos=Diagnostico.query.order_by(Diagnostico.codigo).all(),
                           folio=asignacion.proximo_folio())
@bp.route("/editar/<int:id_receta>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO','UsuarioPasante','Administrador'])
def editar_receta(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)
    
    # SEGURIDAD: No editar si ya hay surtimiento
    if receta.tipo_surtimiento_calculado not in ["No surtida", None]:
        flash("❌ No es posible editar la receta: ya tiene surtimientos registrados.", "danger")
        return redirect(url_for('recetas.detalle_receta', id_receta=id_receta))

    diagnosticos = Diagnostico.query.order_by(Diagnostico.codigo).all()
    todos_medicamentos = Medicamento.query.all()

    if request.method == "POST":
        try:
            # 1. Actualizar Diagnóstico
            receta.diagnostico_id = request.form.get("diagnostico_id")

            # 2. Identificar qué eliminar
            ids_a_eliminar = request.form.getlist("eliminar_detalle")
            
            # 3. Recolectar IDs finales para validar duplicados y límite
            ids_medicamentos_finales = []

            # Procesar existentes que se quedan
            for detalle in receta.detalle:
                if str(detalle.id_detalle) not in ids_a_eliminar:
                    ids_medicamentos_finales.append(str(detalle.id_medicamento))
                    # Actualizar datos del que se queda
                    detalle.cantidad = int(request.form.get(f"cantidad_{detalle.id_detalle}"))
                    detalle.dosis = request.form.get(f"dosis_{detalle.id_detalle}").upper()
                    detalle.indicaciones = request.form.get(f"indicaciones_{detalle.id_detalle}").upper()
                else:
                    db.session.delete(detalle)

            # Procesar nuevos
            nuevos_ids = request.form.getlist("nuevo_medicamento_id[]")
            nuevas_cantidades = request.form.getlist("nuevo_cantidad[]")
            nuevas_dosis = request.form.getlist("nuevo_dosis[]")
            nuevas_inds = request.form.getlist("nuevo_indicaciones[]")

            for i in range(len(nuevos_ids)):
                if nuevos_ids[i]: # Si seleccionó un medicamento
                    ids_medicamentos_finales.append(str(nuevos_ids[i]))
                    nuevo_det = DetalleReceta(
                        id_receta=receta.id_receta,
                        id_medicamento=nuevos_ids[i],
                        cantidad=int(nuevas_cantidades[i]),
                        dosis=nuevas_dosis[i].upper(),
                        indicaciones=nuevas_inds[i].upper()
                    )
                    db.session.add(nuevo_det)

            # --- VALIDACIONES CRÍTICAS ---
            # A. Validar Duplicados
            if len(ids_medicamentos_finales) != len(set(ids_medicamentos_finales)):
                db.session.rollback()
                flash("❌ Error: No se puede recetar el mismo medicamento dos veces.", "danger")
                return redirect(url_for('recetas.editar_receta', id_receta=id_receta))

            # B. Validar Límite de 3
            if len(ids_medicamentos_finales) > 3:
                db.session.rollback()
                flash("❌ Error: Máximo 3 claves por receta.", "danger")
                return redirect(url_for('recetas.editar_receta', id_receta=id_receta))
            
            if len(ids_medicamentos_finales) == 0:
                db.session.rollback()
                flash("❌ Error: La receta debe tener al menos un medicamento.", "danger")
                return redirect(url_for('recetas.editar_receta', id_receta=id_receta))

            db.session.commit()
            flash("✅ Receta actualizada con éxito", "success")
            return redirect(url_for("recetas.detalle_receta", id_receta=receta.id_receta))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar: {str(e)}", "danger")

    return render_template("recetas/editar_receta.html", 
                           receta=receta, 
                           diagnosticos=diagnosticos, 
                           todos_medicamentos=todos_medicamentos)


@bp.route("/salida", methods=["POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def registrar_salida():
    """
    Registro de salida de farmacia:
    - Por medicamento individual: se recibe id_medicamento en form
    - Por receta: se recibe id_receta en form, con cantidades de cada detalle
    """
    id_receta = request.form.get("id_receta")
    id_medicamento = request.form.get("id_medicamento")
    id_medico = int(request.form.get("id_medico", current_user.id_usuario))

    if id_receta:  # Salida por receta completa
        receta = RecetaMedica.query.get_or_404(id_receta)

        for detalle in receta.detalle:
            cantidad_surtida = int(request.form.get(f"med_{detalle.id_medicamento}", 0))
            if cantidad_surtida <= 0:
                continue  # No surtido, se omite

            # Validar inventario
            inventario = InventarioFarmacia.query.filter_by(id_medicamento=detalle.id_medicamento).first()
            if not inventario or inventario.cantidad < cantidad_surtida:
                flash(f"⚠️ No hay suficiente stock para {detalle.medicamento.nombre}", "danger")
                continue

            # Validar bloque y folio del médico
            asignacion = AsignacionReceta.query.filter_by(id_medico=id_medico).order_by(AsignacionReceta.id_asignacion.desc()).first()
            if not asignacion:
                flash(f"⚠️ El médico no tiene bloque asignado", "danger")
                continue
            folio = asignacion.siguiente_folio()
            if not folio:
                flash(f"⚠️ El bloque asignado del médico está agotado", "danger")
                continue

            # Registrar salida
            salida = SalidaFarmaciaPaciente(
                id_medicamento=detalle.id_medicamento,
                cantidad=cantidad_surtida,
                fecha_salida=datetime.utcnow(),
                id_usuario=id_medico,
                folio_receta=receta.folio
            )
            db.session.add(salida)
            inventario.cantidad -= cantidad_surtida

        db.session.commit()
        flash("✅ Salidas de medicamentos registradas.", "success")
        return redirect(url_for("recetas.detalle_receta", id_receta=id_receta))

    elif id_medicamento:  # Salida por medicamento individual
        medicamento = Medicamento.query.get_or_404(id_medicamento)
        cantidad = int(request.form.get("cantidad", 0))
        if cantidad <= 0:
            flash("⚠️ La cantidad debe ser mayor a 0", "danger")
            return redirect(request.referrer or url_for("recetas.listar_salidas"))

        # Inventario
        inventario = InventarioFarmacia.query.filter_by(id_medicamento=id_medicamento).first()
        if not inventario or inventario.cantidad < cantidad:
            flash(f"⚠️ No hay suficiente stock de {medicamento.nombre}", "danger")
            return redirect(request.referrer or url_for("recetas.listar_salidas"))

        # Bloque y folio
        asignacion = AsignacionReceta.query.filter_by(id_medico=id_medico).order_by(AsignacionReceta.id_asignacion.desc()).first()
        if not asignacion:
            flash("⚠️ El médico no tiene bloque asignado", "danger")
            return redirect(request.referrer or url_for("recetas.listar_salidas"))
        folio = asignacion.siguiente_folio()
        if not folio:
            flash("⚠️ El bloque asignado está agotado", "danger")
            return redirect(request.referrer or url_for("recetas.listar_salidas"))

        # Registrar salida
        salida = SalidaFarmaciaPaciente(
            id_medicamento=id_medicamento,
            cantidad=cantidad,
            fecha_salida=datetime.utcnow(),
            id_usuario=id_medico,
            folio_receta=folio
        )
        db.session.add(salida)
        inventario.cantidad -= cantidad
        db.session.commit()

        flash(f"✅ Salida de {medicamento.nombre} registrada con folio {folio}", "success")
        return redirect(request.referrer or url_for("recetas.listar_salidas"))

    else:
        flash("⚠️ No se proporcionó medicamento ni receta", "danger")
        return redirect(request.referrer or url_for("recetas.listar_salidas"))

@bp.route("/salida/detalle_receta/<int:id_receta>", methods=["POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def detalle_recetasss(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)
    
    # Diccionario con cantidades entregadas por medicamento
    entregados = {}
    for salida in receta.salidas:
        entregados[salida.id_medicamento] = entregados.get(salida.id_medicamento, 0) + salida.cantidad

    return render_template(
        "recetas/detalle_receta.html",
        receta=receta,
        entregados=entregados
    )

@bp.route("/detalle/<int:id_receta>")
@roles_required(['USUARIOMEDICO','UsuarioPasante','UsuarioAdministrativo','Administrador'])
def detalle_receta(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)
    
    # Calculamos el total entregado por medicamento (sumando todos sus lotes de salida)
    entregados = {}
    for salida in receta.salidas:
        entregados[salida.id_medicamento] = entregados.get(salida.id_medicamento, 0) + salida.cantidad
    
    return render_template(
        "recetas/detalle_receta.html",
        receta=receta,
        entregados=entregados
    )

#==========================================================================================================surtimiento de receta===============================
@bp.route("/recetas/pendientes")
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def recetas_pendientes():
    query = request.args.get('q', '').strip().upper()
    
    # Base query: recetas no completas con JOIN a Paciente
    recetas_query = RecetaMedica.query.filter(
        RecetaMedica.tipo_surtimiento_calculado != "Completa"
    ).join(Paciente)

    if query:
        # Buscamos por nombre de paciente o intentamos convertir query a folio si es número
        if query.isdigit():
            recetas_query = recetas_query.filter(RecetaMedica.folio == int(query))
        else:
            recetas_query = recetas_query.filter(Paciente.nombre.ilike(f"%{query}%"))

    recetas = recetas_query.order_by(RecetaMedica.fecha_emision.desc()).all()

    return render_template("recetas/pendientes.html", 
                           recetas=recetas, 
                           query=query)

@bp.route("/surtir/<int:id_receta>", methods=["GET", "POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def surtir_receta(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)

    # Diccionario para mostrar stock total disponible por medicamento en el template
    inventario_total = {}
    for det in receta.detalle:
        total = db.session.query(db.func.sum(InventarioFarmacia.cantidad))\
                  .filter_by(id_medicamento=det.id_medicamento).scalar() or 0
        inventario_total[det.id_medicamento] = total

    if request.method == "POST":
        try:
            for det in receta.detalle:
                cant_a_surtir = request.form.get(f"cant_{det.id_detalle}", type=int) or 0
                
                if cant_a_surtir > 0:
                    # Buscamos lotes disponibles en farmacia ordenados por vencimiento (PEPS)
                    lotes_disponibles = InventarioFarmacia.query.filter(
                        InventarioFarmacia.id_medicamento == det.id_medicamento,
                        InventarioFarmacia.cantidad > 0
                    ).order_by(InventarioFarmacia.fecha_vencimiento.asc()).all()

                    por_surtir = cant_a_surtir
                    
                    for inv_lote in lotes_disponibles:
                        if por_surtir <= 0: break
                        
                        cantidad_desde_este_lote = min(inv_lote.cantidad, por_surtir)
                        
                        # 1. Crear registro de salida con el lote específico
                        salida = SalidaFarmaciaPaciente( # Ajustado al nombre de tu modelo de historial
                            id_receta=receta.id_receta,
                            id_medicamento=det.id_medicamento,
                            cantidad=cantidad_desde_este_lote,
                            lote=inv_lote.lote,
                            fecha_vencimiento=inv_lote.fecha_vencimiento,
                            fecha_salida=datetime.utcnow(),
                            id_usuario=current_user.id_usuario
                        )
                        db.session.add(salida)

                        # 2. Restar del inventario de ese lote
                        inv_lote.cantidad -= cantidad_desde_este_lote
                        por_surtir -= cantidad_desde_este_lote

                    # 3. Actualizar el acumulado en la receta
                    det.cantidad_surtida = (det.cantidad_surtida or 0) + cant_a_surtir

            db.session.commit()
            flash(f"✅ Receta {receta.folio} surtida correctamente.", "success")
            return redirect(url_for("recetas.recetas_pendientes"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al surtir: {str(e)}", "danger")

    return render_template("recetas/surtir_receta.html", 
                           receta=receta, 
                           inventario=inventario_total)
