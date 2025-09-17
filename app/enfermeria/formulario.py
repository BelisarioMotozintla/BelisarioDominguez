from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session, jsonify
from flask_login import current_user
from app.models.enfermeria import RegistroAdultoMayor
from app.utils.db import db
from app.utils.validaciones import campos_validos,get_str, get_int, get_date
from app.utils.helpers import roles_required
from . import enfermeria_bp as bp
from io import BytesIO
import pandas as pd
from datetime import datetime, date, time
from sqlalchemy import desc, func
from sqlalchemy.dialects import postgresql
from app.utils.exportador import generar_excel
from app.models.archivo_clinico import Paciente


@bp.route('/formulario', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def formulario():
    if 'usuario' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('auth.login'))

    if session.get('rol') == 'admin':
        return redirect(url_for('admin.panel'))

    usua = session['usuario']
    hoy = date.today()

    # Rango 26 del mes anterior → hoy (en lugar de 25 del mes actual)
    if hoy.month == 1:
        inicio = datetime(hoy.year - 1, 12, 26)
    else:
        inicio = datetime(hoy.year, hoy.month - 1, 26)

    fin = datetime.combine(hoy, datetime.max.time())  # Incluye hoy completo

    # Consulta
    query = RegistroAdultoMayor.query.filter(
        RegistroAdultoMayor.fecha >= inicio,
        RegistroAdultoMayor.fecha <= fin,
        db.func.upper(RegistroAdultoMayor.personal_enfermeria) == usua.upper()
    )
   
    # Ejecutar la query
    registros = query.all()
    
    datos = {}

    if request.method == 'POST':
        # Validar campos obligatorios
        validado, campo = campos_validos(request.form)
        if not validado:
            flash(f"Completa el campo: {campo}", 'danger')
            datos = request.form
            return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

        # Validar fecha principal
        fecha_str = request.form.get('fecha')
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            if fecha_obj < date(1900,1,1) or fecha_obj > date.today():
                flash("Fecha inválida.", "danger")
                datos = request.form
                return render_template('enfermeria/formulario.html', datos=datos, registros=registros)
        except (ValueError, TypeError):
            flash("Formato de fecha incorrecto.", "danger")
            datos = request.form
            return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

        # Validar fecha de nacimiento si existe
        fecha_nac_str = request.form.get('fecha_nacimiento')
        fecha_nac_obj = None
        if fecha_nac_str:
            try:
                fecha_nac_obj = datetime.strptime(fecha_nac_str, '%Y-%m-%d').date()
                if fecha_nac_obj < date(1900,1,1) or fecha_nac_obj > date.today():
                    flash("Fecha de nacimiento inválida.", "danger")
                    datos = request.form
                    return render_template('enfermeria/formulario.html', datos=datos, registros=registros)
            except (ValueError, TypeError):
                flash("Formato de fecha de nacimiento incorrecto.", "danger")
                datos = request.form
                return render_template('enfermeria/formulario.html', datos=datos, registros=registros)
        
        # Guardar registro
        try:
            nuevo_registro = RegistroAdultoMayor(
                unidad_salud = get_str(request.form, 'unidad_salud'),
                entidad_federativa = get_str(request.form, 'entidad_federativa'),
                clues = get_str(request.form, 'clues'),
                localidad = get_str(request.form, 'localidad'),
                servicio = get_str(request.form, 'servicio'),
                personal_enfermeria = usua,
                fecha = fecha_obj,
                hora_inicio = get_str(request.form, 'hora_inicio'),
                hora_termino = get_str(request.form, 'hora_termino'),
                nombre_jefe_fam = get_str(request.form, 'nombre_jefe_fam').upper(),
                paciente = get_str(request.form, 'paciente').upper(),
                fecha_nacimiento = fecha_nac_obj,
                domicilio = get_str(request.form, 'domicilio').upper(),
                edad = get_int(request.form, 'edad'),
                sexo = get_str(request.form, 'sexo'),
                indigena = get_str(request.form, 'indigena'),
                migrante = get_str(request.form, 'migrante'),
                nivel_atencion = get_str(request.form, 'nivel_atencion'),
                consulta_enfermeria = get_str(request.form, 'consulta_enfermeria'),
                consultoria_otorgada = get_str(request.form, 'consultoria_otorgada'),
                prescripcion_medicamentos = get_str(request.form, 'prescripcion_medicamentos'),
                DG_plan_cuidados = get_str(request.form, 'DG_plan_cuidados'),
                DG_GRUPOS_EDAD = get_str(request.form, 'DG_GRUPOS_EDAD'),
                INSTITUCION_PROCEDENCIA = get_str(request.form, 'INSTITUCION_PROCEDENCIA'),
                CONSEJERIA_PF = get_str(request.form, 'CONSEJERIA_PF'),
                PF_GRUPOS_EDAD = get_str(request.form, 'PF_GRUPOS_EDAD'),
                PF_SUBSECUENTE = get_str(request.form, 'PF_SUBSECUENTE'),
                PF_METODO = get_str(request.form, 'PF_METODO'),
                VI_EMB_grupo_edad = get_str(request.form, 'VI_EMB_grupo_edad'),
                VI_EMB_TRIMESTRE_GESTACIONAL = get_str(request.form, 'VI_EMB_TRIMESTRE_GESTACIONAL'),
                VI_EMB_ACCIONES_IRREDUCTIBLES = request.form.getlist('VI_EMB_ACCIONES_IRREDUCTIBLES[]'),
                observaciones = get_str(request.form, 'observaciones'),
                DETECCION_TAMIZ = get_str(request.form, 'DETECCION_TAMIZ'),
                diagnostico_nutricional = get_str(request.form, 'diagnostico_nutricional'),
                SALUD_GINECO_DETECCION = get_str(request.form, 'SALUD_GINECO_DETECCION'),
                EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS = get_str(request.form, 'EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS'),
                EDA_MADRES_CAPACITADAS_MANEJO = get_str(request.form, 'EDA_MADRES_CAPACITADAS_MANEJO'),
                IRA_MADRES_CAPACITADAS_MANEJO = get_str(request.form, 'IRA_MADRES_CAPACITADAS_MANEJO'),
                grupo_riesgo = get_str(request.form, 'grupo_riesgo'),
                DETECCION_ENFERMEDADES_CRONICAS = get_str(request.form, 'DETECCION_ENFERMEDADES_CRONICAS'),
                DIABETES_MELLITUS = get_str(request.form, 'DIABETES_MELLITUS'),
                DISLIPIDEMIA = get_str(request.form, 'DISLIPIDEMIA'),
                hipertension = get_str(request.form, 'hipertension'),
                REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES = get_str(request.form, 'REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES'),
                DIABETICOS_INFORMADOS_CUIDADOS_PIES = get_str(request.form, 'DIABETICOS_INFORMADOS_CUIDADOS_PIES'),
                vacunacion = get_str(request.form, 'vacunacion'),
                PROMOCION_SALUD = get_str(request.form, 'PROMOCION_SALUD'),
                DERIVACION = get_str(request.form, 'DERIVACION'),
                ACTIVIDADES_ASISTENCIALES = get_str(request.form, 'ACTIVIDADES_ASISTENCIALES'),
                OBSERVACIONES_GENERALES = get_str(request.form, 'OBSERVACIONES_GENERALES'),
            )
            db.session.add(nuevo_registro)
            # Actualizar paciente correspondiente
            paciente = Paciente.query.filter_by(nombre=nuevo_registro.paciente).first()
            if paciente:
                # Planificación
                paciente.planificacion = nuevo_registro.PF_METODO not in ["7", None]

                # Embarazo
                # Por ejemplo si hay trimestre gestacional o campo equivalente
                paciente.esta_embarazada = request.form.get("VI_EMB_TRIMESTRE_GESTACIONAL") in ["1", "2", "3"]
                print(request.form.get("VI_EMB_TRIMESTRE_GESTACIONAL"))
                # Enfermedades crónicas
                cronicas = []
                if nuevo_registro.DIABETES_MELLITUS == "2":
                    cronicas.append("Diabético")
                if nuevo_registro.DISLIPIDEMIA == "2":
                    cronicas.append("Metabólico")
                if nuevo_registro.hipertension == "2":
                    cronicas.append("Hipertenso")

                paciente.es_cronico = len(cronicas) > 0
                paciente.tipo_cronicidad = ", ".join(cronicas) if cronicas else "Otro"

            db.session.commit()
            flash('Registro guardado exitosamente.', 'success')
            datos = {}
            registros.append(nuevo_registro)
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {e}', 'danger')
            datos = request.form
            return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

    return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

@bp.route('/exportar', methods=['POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador', 'JefeEnfermeria'])
def exportar():
    if 'usuario' not in session or 'rol' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('auth.login'))

    usuario = session['usuario']
    rol = rol = current_user.rol.nombre_rol

    # Tomar fechas desde el formulario POST
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not fecha_inicio or not fecha_fin:
        flash("Debes seleccionar un rango de fechas.", "warning")
        return redirect(url_for('enfermeria.formulario'))

    try:
        # Llamamos a generar_excel pasando usuario y rol
        excel_output, mensaje = generar_excel(fecha_inicio, fecha_fin, usuario=usuario, rol=rol)

        if not excel_output:
            flash(mensaje, "danger")
            return redirect(url_for('enfermeria.formulario'))

        return send_file(
            excel_output,
            download_name=mensaje,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        flash(f'Error al exportar: {e}', 'danger')
        return redirect(url_for('enfermeria.formulario'))
    
@bp.route('/eliminar', methods=['POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def eliminar():
    ids = request.form.getlist('ids')
    if not ids:
        flash('No se seleccionaron registros para eliminar.', 'warning')
        return redirect(url_for('enfermeria.formulario'))
    registros = RegistroAdultoMayor.query.filter(RegistroAdultoMayor.id.in_(ids)).all()
    for registro in registros:
        db.session.delete(registro)
    db.session.commit()
    flash(f'Se eliminaron {len(registros)} registros.', 'success')
    return redirect(url_for('enfermeria.formulario'))

@bp.route('/consultar', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def consultar():
    resultados = []
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        resultados = RegistroAdultoMayor.query.filter(
            RegistroAdultoMayor.paciente.ilike(f"%{nombre}%")
        ).all()
    return render_template('enfermeria/consulta_nombre.html', resultados=resultados)

@bp.route('/detalle/<int:registro_id>')
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def detalle(registro_id):
    registro = RegistroAdultoMayor.query.get_or_404(registro_id)
    return render_template('enfermeria/detalle.html', registro=registro)

@bp.route('/api/total_capturados_mes', methods=['GET'])
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def total_capturados_mes():
    try:
        usua = session.get('usuario')
        if not usua:
            return jsonify({'error': 'Sesión no válida'}), 401

        hoy = date.today()  # solo fecha, sin hora

        # Día 26 del mes anterior
        if hoy.month == 1:
            inicio = datetime(hoy.year - 1, 12, 26)
        else:
            inicio = datetime(hoy.year, hoy.month - 1, 26)

        # Hasta hoy completo
        fin = datetime.combine(hoy, datetime.max.time())

        print("📅 Rango de fechas:", inicio, "→", fin)
        print("👤 Personal:", usua)

        total = RegistroAdultoMayor.query.filter(
            RegistroAdultoMayor.fecha >= inicio.date(),  # comparar solo fechas
            RegistroAdultoMayor.fecha <= fin.date(),     # comparar solo fechas
            db.func.upper(RegistroAdultoMayor.personal_enfermeria) == usua.upper()
        ).count()

        return jsonify({'total': total})

    except Exception as e:
        print("❌ ERROR total_capturados_mes:", e)
        return jsonify({'error': 'Error al obtener datos'}), 500


@bp.route("/api/reporte", methods=["GET"])
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def reporte_capturas():
    inicio_str = request.args.get("inicio")
    fin_str = request.args.get("fin")
    if not inicio_str or not fin_str:
        return jsonify({"error": "Debes proporcionar 'inicio' y 'fin' en formato YYYY-MM-DD"}), 400
    try:
        inicio = date.fromisoformat(inicio_str)
        fin = date.fromisoformat(fin_str)
    except ValueError:
        return jsonify({"error": "Fechas inválidas; usa formato YYYY-MM-DD"}), 400
    if inicio > fin:
        return jsonify({"error": "La fecha de inicio no puede ser posterior a la fecha de fin"}), 400
    try:
        registros = (
            db.session.query(
                RegistroAdultoMayor.personal_enfermeria,
                func.count(RegistroAdultoMayor.id).label('total')
            )
            .filter(RegistroAdultoMayor.fecha.between(inicio, fin))
            .group_by(RegistroAdultoMayor.personal_enfermeria)
            .order_by(desc('total'))
            .all()
        )
        resultado = [{"personal_enfermeria": r[0], "total": r[1]} for r in registros]
    except Exception as e:
        return jsonify({"error": f"Error al obtener registros: {str(e)}"}), 500
    return jsonify(resultado), 200

@bp.route('/tutorial')
@roles_required(['UsuarioEnfermeria', 'Administrador'])
def tutorial():
    if 'usuario' not in session:
        flash('Inicia sesión para acceder al tutorial.', 'warning')
        return redirect(url_for('admin.auth.login'))
    return render_template('enfermeria/tutorial.html')

@bp.route("/buscar_paciente")
def buscar_paciente():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Buscar coincidencias por nombre (limitamos a 10 resultados)
    resultados = Paciente.query.filter(Paciente.nombre.ilike(f"%{query}%")).limit(10).all()

    # Convertir a lista de dicts con los campos que quieras enviar
    pacientes = []
    for p in resultados:
        pacientes.append({
            "id": p.id_paciente,
            "nombre_completo": p.nombre,
            "sexo": p.sexo,
            "fecha_nacimiento": p.fecha_nacimiento.strftime('%Y-%m-%d'),
            "direccion": p.direccion
        })
    return jsonify(pacientes)
