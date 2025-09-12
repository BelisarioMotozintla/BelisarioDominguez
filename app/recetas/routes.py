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

@bp.route("/salida_lista", methods=["GET"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_salidas():
    # Traer todas las salidas, ordenadas por fecha descendente
    salidas = SalidaFarmaciaPaciente.query.order_by(SalidaFarmaciaPaciente.fecha_salida.desc()).all()
    print(salidas)
    print(len(salidas))
    
    # Asegurarse de que cada salida tenga acceso a receta, medicamento y usuario
    return render_template("recetas/listar_salidas.html", salidas=salidas)

@bp.route("/recetas/crear/<int:id_nota>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO','UsuarioPasante','Administrador'])
def crear_receta(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
   
    # Obtener la consulta a través de la nota
    consulta = nota.consulta  
    paciente = consulta.paciente  

    # Traer medicamentos + existencia en farmacia
    medicamentos = [
        {
            "id": m.id_medicamento,
            "descripcion": f"{m.nombre_comercial} {m.presentacion} {m.concentracion} (Clave: {m.clave})",
            "existencia": inv.cantidad if inv else 0
        }
        for m, inv in db.session.query(Medicamento, InventarioFarmacia).outerjoin(
            InventarioFarmacia, InventarioFarmacia.id_medicamento == Medicamento.id_medicamento
        )
    ]

    # Diagnósticos disponibles
    diagnosticos = Diagnostico.query.order_by(Diagnostico.codigo).all()

    # Médico logueado
    id_medico = current_user.id_usuario

    # Última asignación de folios para ese médico
    asignacion = AsignacionReceta.query.filter_by(id_medico=id_medico) \
                                      .order_by(AsignacionReceta.id_asignacion.desc()).first()

    if not asignacion:
        flash("⚠️ No tienes bloque de recetas asignado.", "danger")
        return redirect(url_for('medicos.menu_medico'))

    # Folio solo para mostrar (no se consume aún)
    folio_mostrar = asignacion.proximo_folio()

    if request.method == "POST":
        # Consumir el folio real
        folio = asignacion.siguiente_folio()
        if not folio:
            flash("⚠️ Tu bloque asignado ya está agotado.", "danger")
            return redirect(url_for('recetas.crear_receta', id_nota=id_nota))

        # Crear la receta
        receta = RecetaMedica(
            id_asignacion=asignacion.id_asignacion,
            id_paciente=paciente.id_paciente,
            id_usuario=id_medico,
            folio=folio,
            nota_id=nota.id_nota,
            diagnostico_id=request.form.get("diagnostico_id")  # 🔹 ahora también se guarda el diagnóstico
        )
        db.session.add(receta)
        db.session.flush()  # obtener id_receta

        # Guardar hasta 3 medicamentos con dosis e indicaciones
        for i in range(1, 4):
            id_med = request.form.get(f"med_{i}")
            cantidad = request.form.get(f"cant_{i}")
            dosis = request.form.get(f"dosis_{i}")
            indicaciones = request.form.get(f"indicaciones_{i}")

            if id_med and cantidad:
                detalle = DetalleReceta(
                    id_receta=receta.id_receta,
                    id_medicamento=int(id_med),
                    cantidad=int(cantidad),
                    dosis=dosis,
                    indicaciones=indicaciones
                )
                db.session.add(detalle)

        db.session.commit()
        flash(f"✅ Receta creada con folio {folio}", "success")
        return redirect(url_for("recetas.detalle_receta", id_receta=receta.id_receta))

    # Renderizar formulario
    return render_template(
        "recetas/crear_receta.html",
        nota=nota,
        consulta=consulta,
        paciente=paciente,
        medicamentos=medicamentos,
        diagnosticos=diagnosticos,
        folio=folio_mostrar
    )

@bp.route("/editar/<int:id_receta>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO','UsuarioPasante','Administrador'])
def editar_receta(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)
    diagnosticos = Diagnostico.query.order_by(Diagnostico.codigo).all()

    if request.method == "POST":
        try:
            # Actualizar diagnóstico
            receta.diagnostico_id = request.form.get("diagnostico_id", receta.diagnostico_id)

            # Actualizar cada detalle de medicamento
            for detalle in receta.detalle:
                cantidad = request.form.get(f"cantidad_{detalle.id_detalle}")
                dosis = request.form.get(f"dosis_{detalle.id_detalle}")
                indicaciones = request.form.get(f"indicaciones_{detalle.id_detalle}")

                if cantidad:
                    detalle.cantidad = int(cantidad)
                detalle.dosis = dosis
                detalle.indicaciones = indicaciones

            db.session.commit()
            flash("✅ Receta actualizada con éxito", "success")
            return redirect(url_for("recetas.detalle_receta", id_receta=receta.id_receta))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al actualizar la receta: {e}", "danger")

    return render_template(
        "recetas/editar_receta.html",
        receta=receta,
        diagnosticos=diagnosticos
    )


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
    
    # Diccionario con cantidades entregadas por medicamento
    entregados = {s.id_medicamento: s.cantidad for s in receta.salidas}
    
    # Lista de médicos
    medicos = Usuario.query.all()
    
    return render_template(
        "recetas/detalle_receta.html",
        receta=receta,
        entregados=entregados,
        medicos=medicos
    )
#==========================================================================================================surtimiento de receta===============================
@bp.route("/recetas/pendientes")
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def recetas_pendientes():
    # Obtener parámetros de búsqueda
    folio = request.args.get("folio", type=int)
    paciente_nombre = request.args.get("paciente", type=str)

    # Base query: solo recetas que no estén completas
    query = RecetaMedica.query.filter(
        RecetaMedica.tipo_surtimiento_calculado != "Completa"
    ).join(Paciente)

    # Filtrar por folio si se especifica
    if folio:
        query = query.filter(RecetaMedica.folio == folio)

    # Filtrar por nombre de paciente si se especifica
    if paciente_nombre:
        query = query.filter(Paciente.nombre.ilike(f"%{paciente_nombre}%"))

    # Ordenar por fecha descendente
    recetas = query.order_by(RecetaMedica.fecha_emision.desc()).all()

    return render_template(
        "recetas/pendientes.html",
        recetas=recetas
    )

@bp.route("/surtir/<int:id_receta>", methods=["GET", "POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def surtir_receta(id_receta):
    receta = RecetaMedica.query.get_or_404(id_receta)

    # Inventario actual por medicamento
    inventario = {
        det.id_medicamento: (
            db.session.query(InventarioFarmacia)
            .filter_by(id_medicamento=det.id_medicamento)
            .first().cantidad
            if db.session.query(InventarioFarmacia).filter_by(id_medicamento=det.id_medicamento).first()
            else 0
        )
        for det in receta.detalle
    }

    if request.method == "POST":
        try:
            for det in receta.detalle:
                cant_entregada = request.form.get(f"cant_{det.id_detalle}", type=int) or 0

                # Validar que no se surta más de lo recetado
                cant_max = det.cantidad - (det.cantidad_surtida or 0)
                if cant_entregada > cant_max:
                    cant_entregada = cant_max

                # Validar que no se surta más de lo disponible
                stock = inventario[det.id_medicamento]
                if cant_entregada > stock:
                    cant_entregada = stock

                if cant_entregada > 0:
                    # Crear registro de salida en farmacia
                    salida = SalidaFarmaciaPaciente(
                        folio_receta=receta.folio,   # ✅ Campo correcto
                        id_medicamento=det.id_medicamento,
                        cantidad=cant_entregada,
                        fecha_salida=datetime.utcnow(),
                        id_usuario=current_user.id_usuario
                    )
                    db.session.add(salida)

                    # Actualizar inventario
                    inv = InventarioFarmacia.query.filter_by(id_medicamento=det.id_medicamento).first()
                    if inv:
                        inv.cantidad = max(inv.cantidad - cant_entregada, 0)

                    # Actualizar cantidad surtida en DetalleReceta
                    det.cantidad_surtida = (det.cantidad_surtida or 0) + cant_entregada

            db.session.commit()
            flash("✅ Receta surtida correctamente", "success")
            return redirect(url_for("recetas.recetas_pendientes"))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al surtir la receta: {e}", "danger")

    return render_template("recetas/surtir_receta.html", receta=receta, inventario=inventario)
