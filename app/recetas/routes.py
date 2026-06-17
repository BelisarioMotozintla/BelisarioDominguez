# app/recetas/routes.py
from flask import Blueprint, request, render_template, redirect, url_for, flash,send_file,current_app
from app import db
from datetime import datetime, timezone 
from app.models import BloqueReceta, AsignacionReceta, Usuario,Roles, RecetaMedica,InventarioFarmacia,Medicamento,DetalleReceta,Diagnostico,SalidaFarmacia
from app.models.medicos import NotaConsultaExterna
from app.models.archivo_clinico import  Paciente
from app.utils.helpers import roles_required
from flask_login import current_user
import os
import tempfile
import subprocess
from io import BytesIO
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter


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
from flask import render_template, request, url_for
from flask_login import current_user
from sqlalchemy import cast, String
from collections import defaultdict
from datetime import datetime

@bp.route('/salidas/listar')
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def listar_salidas():
    query = request.args.get('q', '').strip()
    
    # 1. Consulta base con Joins cargados
    salidas_query = SalidaFarmacia.query\
        .outerjoin(Medicamento)\
        .outerjoin(RecetaMedica)\
        .outerjoin(Paciente)

    # 2. Restricción por rol utilizando tu modelo real (nombre_rol)
    es_admin = False
    if current_user.is_authenticated and current_user.rol:
        if current_user.rol.nombre_rol == 'Administrador':
            es_admin = True

    # Si NO es administrador, se restringe a que solo vea sus capturas
    if not es_admin:
        salidas_query = salidas_query.filter(SalidaFarmacia.id_usuario == current_user.id_usuario)

    # 3. Filtros activos del buscador predictivo
    if query:
        search = f"%{query}%"
        salidas_query = salidas_query.filter(
            (cast(RecetaMedica.folio, String).ilike(search)) |
            (Paciente.nombre.ilike(search)) |
            (Medicamento.principio_activo.ilike(search)) |
            (SalidaFarmacia.lote.ilike(search))
        )

    # 4. Obtener todos los registros ordenados por fecha
    salidas = salidas_query.order_by(SalidaFarmacia.fecha_salida.desc()).all()

    # =========================================================
    # LÓGICA DE AUDITORÍA: PROCESAMIENTO DE INDICADORES DIARIOS
    # =========================================================
    dicc_dias = {}

    for s in salidas:
        dia = s.fecha_salida.day
        
        if dia not in dicc_dias:
            dicc_dias[dia] = {
                "dia": dia,
                "folios_lista": [],       
                "recetas_set": set(),     
                "claves_set": set(),      
                "claves_negadas_set": set(),
                "piezas_surtidas": 0,
                "piezas_negadas": 0,
                "surtidas_count": 0,
                "parciales_count": 0,
                "negadas_count": 0,
                "detalles_salidas": []    
            }
        
        d_datos = dicc_dias[dia]
        d_datos["detalles_salidas"].append(s)
        
        if s.receta:
            folio = s.receta.folio or "S/F"
            # USAMOS LA PROPIEDAD REAL DE TU MODELO
            estado_receta = s.receta.tipo_surtimiento_calculado
            
            folio_ya_registrado = any(f["folio"] == folio for f in d_datos["folios_lista"])
            if not folio_ya_registrado:
                d_datos["folios_lista"].append({
                    "folio": folio,
                    "id_receta": s.id_receta,
                    "estado": estado_receta
                })
            
            # Contadores adaptados a los retornos de tu @property ("Completa", "Parcial", "No surtida")
            if folio not in d_datos["recetas_set"]:
                d_datos["recetas_set"].add(folio)
                if estado_receta == "Completa":
                    d_datos["surtidas_count"] += 1
                elif estado_receta == "Parcial":
                    d_datos["parciales_count"] += 1
                elif estado_receta == "No surtida":
                    d_datos["negadas_count"] += 1

        if s.medicamento:
            clave = s.medicamento.clave
            if s.cantidad > 0:
                d_datos["claves_set"].add(clave)
                d_datos["piezas_surtidas"] += s.cantidad
            else:
                d_datos["claves_negadas_set"].add(clave)
                d_datos["piezas_negadas"] += 1

    reporte_dias = [dicc_dias[d] for d in sorted(dicc_dias.keys())]

    for d in reporte_dias:
        d["total_claves_surtidas"] = len(d["claves_set"])
        d["total_claves_negadas"] = len(d["claves_negadas_set"])

    return render_template('recetas/listar_salidas.html', 
                           salidas=salidas, 
                           query=query,
                           es_admin=es_admin,
                           reporte_dias=reporte_dias)






# crear recetas express
@bp.route("/recetas/express", methods=["POST"])
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def crear_receta_express():
    # 🔹 CAMBIO 1: Recibir el folio como String limpio y en mayúsculas (Soporta "JR0151")
    folio = request.form.get("folio", "").upper().strip()
    id_despachador = current_user.id_usuario
    
    # Validamos que el campo no llegue vacío tras la limpieza
    if not folio:
        flash("❌ El folio de la receta es obligatorio.", "danger")
        return redirect(url_for("recetas.recetas_pendientes"))
    
    # Validamos duplicidad de folios manuales alfanuméricos
    if RecetaMedica.query.filter_by(folio=folio).first():
        flash(f"❌ El folio {folio} ya fue registrado anteriormente.", "danger")
        return redirect(url_for("recetas.recetas_pendientes"))

    try:
        # 1. Insertamos la receta omitiendo campos médicos y dejando id_paciente en un ID genérico
        nueva_receta = RecetaMedica(
            folio=folio, # 🔹 Se guarda la cadena de texto limpia
            id_paciente=64,
            id_asignacion=2,          
            nota_id=5,
            diagnostico_id=1,
            id_usuario=id_despachador, 
            fecha_emision=datetime.now(timezone.utc) # Actualizado para Python 3.12+
        )
        db.session.add(nueva_receta)
        db.session.flush() # Genera el id_receta

        # 2. Capturar los tres bloques de medicamentos del formulario modal
        for i in range(1, 4):
            id_med = request.form.get(f"medicamento_{i}", type=int)
            cant_recetada = request.form.get(f"recetado_{i}", type=int) or 0
            cant_surtida = request.form.get(f"surtido_{i}", type=int) or 0

            if id_med and cant_recetada > 0:
                detalle = DetalleReceta(
                    id_receta=nueva_receta.id_receta,
                    id_medicamento=id_med,
                    cantidad=cant_recetada,
                    cantidad_surtida=cant_surtida,
                    dosis="CAPTURADO EN FARMACIA",
                    indicaciones="SURTIDO DIRECTO"
                )
                db.session.add(detalle)

                # 3. Lógica de almacén de farmacia (Consumo automático FIFO)
                if cant_surtida > 0:
                    lotes_disponibles = InventarioFarmacia.query.filter(
                        InventarioFarmacia.id_medicamento == id_med,
                        InventarioFarmacia.cantidad > 0
                    ).order_by(InventarioFarmacia.fecha_vencimiento.asc()).all()

                    por_surtir = cant_surtida
                    
                    for inv_lote in lotes_disponibles:
                        if por_surtir <= 0: 
                            break
                        
                        cantidad_desde_este_lote = min(inv_lote.cantidad, por_surtir)

                        # 🔹 CAMBIO 2: Grabamos usando la nueva tabla especializada del "Abanico de Salidas"
                        salida = SalidaFarmacia(
                            id_medicamento=id_med,
                            cantidad=cantidad_desde_este_lote,
                            lote=inv_lote.lote,
                            fecha_vencimiento=inv_lote.fecha_vencimiento,
                            fecha_salida=datetime.now(timezone.utc),
                            id_usuario=id_despachador,
                            
                            # Campos especializados del abanico para flujo de recetas
                            tipo_salida='RECETA',
                            id_receta=nueva_receta.id_receta,
                            entidad_destino=None, # Queda nulo porque va a un paciente
                            documento_soporte=f"RECETA EXPRESS FOLIO: {folio}"
                        )
                        db.session.add(salida)

                        # Modificamos la existencia del lote
                        inv_lote.cantidad -= cantidad_desde_este_lote
                        por_surtir -= cantidad_desde_este_lote

                        # Opcional: si el lote queda en 0, lo removemos del anaquel activo
                        if inv_lote.cantidad == 0:
                            db.session.delete(inv_lote)

        db.session.commit()
        flash(f"⚡ Receta física Folio {folio} guardada y descontada del inventario correctamente.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al procesar la captura de farmacia: {str(e)}", "danger")

    return redirect(url_for("recetas.recetas_pendientes"))

@bp.route("/recetas/crear/<int:id_nota>", methods=["GET", "POST"])
@roles_required(['USUARIOMEDICO', 'UsuarioPasante', 'Administrador'])
def crear_receta(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    consulta = nota.consulta
    paciente = consulta.paciente
    id_medico = current_user.id_usuario

    # ==========================================
    # MEDICAMENTOS CON EXISTENCIA EN FARMACIA
    # ==========================================
    medicamentos_db = db.session.query(
        Medicamento,
        InventarioFarmacia
    ).outerjoin(
        InventarioFarmacia,
        InventarioFarmacia.id_medicamento == Medicamento.id_medicamento
    ).all()

    medicamentos = [
        {
            "id": m.id_medicamento,
            "descripcion": f"{m.clave} - {m.principio_activo} ({m.presentacion})",
            "existencia": inv.cantidad if inv else 0
        }
        for m, inv in medicamentos_db
    ]

    # ==========================================
    # BLOQUE DE FOLIOS DEL MÉDICO
    # ==========================================
    asignacion = AsignacionReceta.query.filter_by(
        id_medico=id_medico
    ).order_by(
        AsignacionReceta.id_asignacion.desc()
    ).first()

    if not asignacion:
        flash(
            "⚠️ No tienes un bloque de recetas asignado. Contacta al administrador.",
            "danger"
        )
        return redirect(url_for('medicos.ver_nota', id_nota=id_nota))

    # ==========================================
    # POST
    # ==========================================
    if request.method == "POST":

        folio = asignacion.siguiente_folio()

        if not folio:
            flash("⚠️ Tu bloque de folios se ha agotado.", "danger")
            return redirect(request.url)

        try:
            # ==================================
            # CREAR RECETA
            # ==================================
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

            # ==================================
            # CAPTURAR LISTAS DEL FORMULARIO
            # ==================================
            med_ids = request.form.getlist("med_ids[]")
            cantidades = request.form.getlist("cantidades[]")
            dosis_list = request.form.getlist("dosis[]")
            indicaciones_list = request.form.getlist("indicaciones[]")

            # ==================================
            # GUARDAR DETALLES
            # ==================================
            for i in range(len(med_ids)):

                id_med = med_ids[i].strip()
                cant = cantidades[i].strip()

                dosis = (
                    dosis_list[i].strip().upper()
                    if i < len(dosis_list) and dosis_list[i]
                    else ""
                )

                indicaciones = (
                    indicaciones_list[i].strip().upper()
                    if i < len(indicaciones_list) and indicaciones_list[i]
                    else ""
                )

                if id_med and cant:

                    detalle = DetalleReceta(
                        id_receta=nueva_receta.id_receta,
                        id_medicamento=int(id_med),
                        cantidad=int(cant),
                        dosis=dosis,
                        indicaciones=indicaciones
                    )

                    db.session.add(detalle)

            # ==================================
            # GUARDAR
            # ==================================
            db.session.commit()

            flash(
                f"✅ Receta folio {folio} creada exitosamente.",
                "success"
            )

            return redirect(
                url_for(
                    "recetas.detalle_receta",
                    id_receta=nueva_receta.id_receta
                )
            )

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error al crear receta: {str(e)}", "danger")

    # ==========================================
    # GET
    # ==========================================
    return render_template(
        "recetas/crear_receta.html",
        nota=nota,
        consulta=consulta,
        paciente=paciente,
        medicamentos=medicamentos,
        diagnosticos=Diagnostico.query.order_by(
            Diagnostico.codigo
        ).all(),
        folio=asignacion.proximo_folio()
    )

from flask import flash, redirect, url_for
from app import db # Ajusta el import de tu base de datos
from app.models import RecetaMedica, InventarioFarmacia # Ajusta tus modelos

@bp.route("/recetas/eliminar/<int:id_receta>", methods=["POST"])
@roles_required(['Administrador'])
def eliminar_receta(id_receta):
    # 1. Buscar la receta pendiente
    receta = RecetaMedica.query.get_or_404(id_receta)
    
    try:
        # 2. ESCENARIO "YA SURTÍ ALGO" (Surtido Parcial): Devolver stock antes de borrar
        if receta.salidas:
            for salida in receta.salidas:
                # Buscamos el lote exacto en el inventario de la farmacia
                inventario_lote = InventarioFarmacia.query.filter_by(
                    id_medicamento=salida.id_medicamento,
                    lote=salida.lote
                ).first()

                if inventario_lote:
                    # Devolvemos las piezas al lote original
                    inventario_lote.cantidad += salida.cantidad
                else:
                    # Si el lote ya no existía en el inventario, lo recreamos
                    nuevo_lote = InventarioFarmacia(
                        id_medicamento=salida.id_medicamento,
                        lote=salida.lote,
                        cantidad=salida.cantidad,
                        fecha_vencimiento=salida.fecha_vencimiento
                    )
                    db.session.add(nuevo_lote)
                
                # Borramos el registro del historial de salidas vinculado a esta receta
                db.session.delete(salida)

        # 3. ESCENARIO "NO HE SURTIDO" / LIMPIEZA: Borrar renglones de la receta
        for detalle in receta.detalle:
            db.session.delete(detalle)
            
        # 4. Borrar la receta principal
        db.session.delete(receta)
        
        # Guardar todos los cambios en la Base de Datos
        db.session.commit()
        flash(f"🗑️ Receta con folio {receta.folio} eliminada correctamente. El stock parcial fue devuelto a los anaqueles.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Error al intentar eliminar la receta: {str(e)}", "danger")
        
    # 5. Redireccionar siempre al listado de pendientes
    return redirect(url_for("recetas.recetas_pendientes"))

@bp.route('/salidas/eliminar/<int:id>', methods=['POST'])
@roles_required(['Administrador'])
def eliminar_salida(id):
    # 1. Buscar el registro de la salida (el historial)
    salida = SalidaFarmacia.query.get_or_404(id)
    
    try:
        # 2. LÓGICA DE STOCK REAL: Buscar el lote exacto en el inventario para devolver las piezas
        inventario_lote = InventarioFarmacia.query.filter_by(
            id_medicamento=salida.id_medicamento,
            lote=salida.lote
        ).first()

        if inventario_lote:
            # Si el lote aún existe en el inventario, le sumamos las piezas devueltas
            inventario_lote.cantidad += salida.cantidad
        else:
            # Si por alguna razón el lote ya se había borrado (cantidad 0), lo volvemos a crear
            nuevo_lote = InventarioFarmacia(
                id_medicamento=salida.id_medicamento,
                lote=salida.lote,
                cantidad=salida.cantidad,
                fecha_vencimiento=salida.fecha_vencimiento
            )
            db.session.add(nuevo_lote)

        # 3. Restar la cantidad surtida del detalle de la receta (si es que está asociada a una)
        if salida.id_receta:
            # Buscamos el renglón específico de ese medicamento en esa receta
            # Nota: Ajusta 'id_receta' o los nombres según tus modelos de receta.detalle
            from app.models import RecetaDetalle # O el nombre exacto de tu modelo de detalles
            detalle_receta = RecetaDetalle.query.filter_by(
                id_receta=salida.id_receta,
                id_medicamento=salida.id_medicamento
            ).first()
            
            if detalle_receta and detalle_receta.cantidad_surtida:
                # Restamos la cantidad para que la receta pueda volver a figurar como pendiente/parcial
                detalle_receta.cantidad_surtida -= salida.cantidad
                if detalle_receta.cantidad_surtida < 0:
                    detalle_receta.cantidad_surtida = 0

        # 4. Eliminar el registro del historial de salidas
        db.session.delete(salida)
        db.session.commit()
        flash('✅ Salida revertida con éxito. El stock ha regresado al lote correspondiente en la farmacia.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error al intentar revertir la salida: {str(e)}', 'danger')
        
    # 5. Redireccionar de vuelta al listado de salidas
    return redirect(url_for('recetas.listar_salidas'))


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
            salida = SalidaFarmacia(
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
        salida = SalidaFarmacia(
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

def generar_base_folio(nombre, ap_paterno):
    if nombre and ap_paterno:
        return f"{nombre.strip().upper()[0]}{ap_paterno.strip().upper()[0]}"
    return "XX"

@bp.route('/imprimir/<int:id_receta>/pdf')
@roles_required([
    'USUARIOMEDICO',
    'UsuarioPasante',
    'UsuarioAdministrativo',
    'Administrador'
])
def receta_pdf(id_receta):
    try:
        receta = RecetaMedica.query.get_or_404(id_receta)
        paciente = receta.paciente
        medico = receta.usuario
        diagnostico = receta.diagnostico

        plantilla = os.path.join(current_app.root_path, 'static', 'receta', 'receta.pdf')

        if not os.path.exists(plantilla):
            flash("No se encontró receta.pdf", "danger")
            return redirect(url_for('recetas.detalle_receta', id_receta=id_receta))

        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Times-BoldItalic", 10)

        # ==================================================
        # EXTRACCIÓN DE DATOS Y CÁLCULOS
        # ==================================================
        emp = receta.usuario.empleado 
        nombre = paciente.nombre if paciente else ""
        expediente = str(paciente.id_paciente) if paciente else ""
        dx = diagnostico.descripcion if diagnostico else ""
        doctor = f"{emp.nombre} {emp.apellido_paterno} {emp.apellido_materno}".strip()
        fecha = receta.fecha_emision.strftime("%d/%m/%Y")
        
        # Fecha de Nacimiento y Sexo
        f_nac = paciente.fecha_nacimiento.strftime("%d/%m/%Y") if paciente and paciente.fecha_nacimiento else ""
        sexo_val = paciente.sexo.upper() if paciente and paciente.sexo else ""
        cedula = emp.cedula if emp and hasattr(emp, 'cedula') else ""
        servicio_nombre = receta.nota.servicio.nombre_servicio.upper() if receta.nota and receta.nota.servicio else "GENERAL"

        # 2. Definir coordenadas según el servicio
        if "EXTERNA" in servicio_nombre:
            c.drawString(220, 680, f"X")# ARRIBA 
            c.drawString(220, 285, f"X")#ABAJO
        elif "URGENCIA" in servicio_nombre:
            c.drawString(305, 680, f"X")# ARRIBA
            c.drawString(305, 285, f"X")#ABAJO
        else:
            c.drawString(365, 680, f"X")# ARRIBA
            c.drawString(365, 285, f"X")#ABAJO

     
                
        # Cálculo de Edad
        edad_str = ""
        if paciente and paciente.fecha_nacimiento:
            from datetime import date
            today = date.today()
            born = paciente.fecha_nacimiento
            edad = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            edad_str = str(edad)

        detalles = receta.detalle[:3]

        # ==================================================
        # POSICIONES ORIGINAL ARRIBA
        # ==================================================
        
        folio_limpio = generar_base_folio(emp.nombre,emp.apellido_paterno) 
        c.drawString(505, 730, f"{folio_limpio}{str(receta.folio).zfill(5)}")
        #   POR SI ALGUN DIA NO INTERO EL FOLIO     c.drawString(505, 730, f"{folio_limpio}{str(receta.folio).zfill(5)}")
        c.drawString(10, 680, nombre)
        c.drawString(20, 660, expediente)
        c.drawString(505, 700, fecha)
        c.drawString(370, 660, dx[:35])
        c.drawString(10, 480, doctor)
        c.drawString(360, 480, f" {cedula}")
        
        # Edad y Fecha Nacimiento
        c.drawString(170, 660, f" {edad_str}")
        c.drawString(80, 660, f" {f_nac}")

        # Marcar Sexo con X Arriba
        if sexo_val in ['M', 'HOMBRE', 'MASCULINO']:
            c.drawString(220, 660, "X") # Ajusta esta X para el cuadrito Hombre
        elif sexo_val in ['F', 'MUJER', 'FEMENINO']:
            c.drawString(305, 660, "X") # Ajusta esta X para el cuadrito Mujer

        # Medicamentos e Indicaciones Arriba
        if len(detalles) >= 1:
            med = detalles[0].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, 635, (texto_med if detalles[0].medicamento else "")[:100])
            c.drawString(507, 635, str(detalles[0].cantidad))
            c.drawString(10, 620, f"{detalles[0].dosis} {detalles[0].indicaciones}"[:95])

        if len(detalles) >= 2:
            med = detalles[1].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, 585, (texto_med  if detalles[1].medicamento else "")[:100])
            c.drawString(507, 585, str(detalles[1].cantidad))
            c.drawString(10, 570, f"{detalles[1].dosis} {detalles[1].indicaciones}"[:95])

        if len(detalles) >= 3:
            med = detalles[2].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, 530, (texto_med if detalles[2].medicamento else "")[:100])
            c.drawString(507, 530, str(detalles[2].cantidad))
            c.drawString(10, 510, f"{detalles[2].dosis} {detalles[2].indicaciones}"[:95])

        # ==================================================
        # COPIA ABAJO
        # ==================================================
        
        c.drawString(505, 340,  f"{folio_limpio}{str(receta.folio).zfill(5)}")
        c.drawString(10, 285, nombre)
        c.drawString(20, 260, expediente)
        c.drawString(505, 315, fecha)
        c.drawString(370, 260, dx[:35])
        c.drawString(10, 85, doctor)
        c.drawString(360, 85, f" {cedula}")

        # Edad y Fecha Nacimiento
        c.drawString(170, 260, f" {edad_str}")
        c.drawString(80, 260, f" {f_nac}")

        # Marcar Sexo con X Abajo
        if sexo_val in ['M', 'HOMBRE', 'MASCULINO']:
            c.drawString(220, 260, "X") # Ajusta según tu PDF de abajo
        elif sexo_val in ['F', 'MUJER', 'FEMENINO']:
            c.drawString(305, 260, "X") # Ajusta según tu PDF de abajo

        # Medicamentos e Indicaciones Abajo
        filas_med_abajo = [235, 185, 135]
        if len(detalles) >= 1:
            med = detalles[0].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, filas_med_abajo[0], (texto_med if detalles[0].medicamento else "")[:100])
            c.drawString(507, filas_med_abajo[0], str(detalles[0].cantidad))
            c.drawString(10, 215, f"{detalles[0].dosis} {detalles[0].indicaciones}"[:95])

        if len(detalles) >= 2:
            med = detalles[1].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, filas_med_abajo[1], (texto_med if detalles[1].medicamento else "")[:100])
            c.drawString(507, filas_med_abajo[1], str(detalles[1].cantidad))
            c.drawString(10, 165, f"{detalles[1].dosis} {detalles[1].indicaciones}"[:95])

        if len(detalles) >= 3:
            med = detalles[2].medicamento
            texto_med = f"{med.clave} - {med.principio_activo} ({med.concentracion}, {med.presentacion})"
            c.drawString(10, filas_med_abajo[2], (texto_med if detalles[2].medicamento else "")[:100])
            c.drawString(507, filas_med_abajo[2], str(detalles[2].cantidad))
            c.drawString(10, 110, f"{detalles[2].dosis} {detalles[2].indicaciones}"[:95])

        c.save()

        # ==================================================
        # MEZCLA Y SALIDA
        # ==================================================
        packet.seek(0)
        nuevo_pdf = PdfReader(packet)
        with open(plantilla, "rb") as f:
            base_pdf = PdfReader(f)
            writer = PdfWriter()
            pagina = base_pdf.pages[0]
            pagina.merge_page(nuevo_pdf.pages[0])
            writer.add_page(pagina)
            salida = BytesIO()
            writer.write(salida)
            salida.seek(0)

        return send_file(salida, as_attachment=True, download_name=f"Receta_{receta.folio}.pdf", mimetype="application/pdf")

    except Exception as e:
        flash(f"Error al generar receta PDF: {str(e)}", "danger")
        return redirect(url_for('recetas.detalle_receta', id_receta=id_receta))


#==========================================================================================================surtimiento de receta===============================
from app.models import RecetaMedica, Paciente, Medicamento, InventarioFarmacia
from sqlalchemy import func
@bp.route("/recetas/pendientes")
@roles_required(['UsuarioAdministrativo', 'Administrador'])
def recetas_pendientes():
    query = request.args.get('q', '').strip().upper()
    
    # Usamos outerjoin con Paciente por si existen recetas previas sin paciente ligado
    recetas_query = RecetaMedica.query.outerjoin(Paciente)

    if query:
        # Buscador alfanumérico que acepta folios con letras como "JR0151" o nombres
        recetas_query = recetas_query.filter(
            (RecetaMedica.folio.ilike(f"%{query}%")) | 
            (Paciente.nombre.ilike(f"%{query}%"))
        )

    todas_las_recetas = recetas_query.order_by(RecetaMedica.fecha_emision.desc()).all()
    recetas_filtradas = [r for r in todas_las_recetas if r.tipo_surtimiento_calculado != "Completa"]

    # Catálogo tradicional de medicamentos (Mantenemos tu query original intacta)
    medicamentos_db = db.session.query(
        Medicamento,
        InventarioFarmacia
    ).outerjoin(
        InventarioFarmacia,
        InventarioFarmacia.id_medicamento == Medicamento.id_medicamento
    ).all()

    # 🌟 AQUÍ ESTÁ LA SOLUCIÓN DE LOS CEROS:
    # Aseguramos el mapeo de variables usando los atributos exactos de tu modelo Medicamento
    medicamentos = []
    
    for m, inv in medicamentos_db:
        # Extraemos de forma segura los valores de las columnas unificadas
        clave_real = m.clave if m.clave else "S/C"
        principio = m.principio_activo if m.principio_activo else "SIN NOMBRE"
        presentacion = f" ({m.presentacion})" if m.presentacion else ""
        
        medicamentos.append({
            "id": m.id_medicamento,  # Vincula el ID real de la base de datos
            "clave": clave_real,     # Llena tu campo {{ m.clave }}
            "descripcion": f"{principio}{presentacion}", # Llena tu campo {{ m.descripcion }}
            "existencia": inv.cantidad if inv else 0      # Llena tu campo {{ m.existencia }}
        })
        
		
    return render_template("recetas/pendientes.html", 
                           recetas=recetas_filtradas, 
                           query=query,
                           medicamentos=medicamentos)


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
                        salida = SalidaFarmacia( # Ajustado al nombre de tu modelo de historial
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
