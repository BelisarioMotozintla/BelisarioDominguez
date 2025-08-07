from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session, jsonify
from app.models.enfermeria import RegistroAdultoMayor
from app.utils.db import db
from app.utils.validaciones import campos_validos,get_str, get_int, get_date
from app.utils.helpers import login_required
from . import enfermeria_bp as bp
from io import BytesIO
import pandas as pd
from datetime import datetime, date
from sqlalchemy import desc, func



@bp.route('/formulario', methods=['GET', 'POST'])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def formulario():
    if 'usuario' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('auth.login'))

    if session.get('rol') == 'admin':
        return redirect(url_for('admin.panel'))

    usua = session['usuario']
    hoy = date.today()

    # Rango fechas del 26 del mes anterior al 25 del actual
    if hoy.month == 1:
        inicio = datetime(hoy.year - 1, 12, 26)
    else:
        inicio = datetime(hoy.year, hoy.month - 1, 26)
    fin = datetime(hoy.year, hoy.month, 25, 23, 59, 59)

    registros = RegistroAdultoMayor.query.filter(
        RegistroAdultoMayor.fecha >= inicio,
        RegistroAdultoMayor.fecha <= fin,
        RegistroAdultoMayor.personal_enfermeria == usua
    ).all()

    datos = {}  # Diccionario para enviar datos al formulario

    if request.method == 'POST':
        # Si el POST es para búsqueda por nombre (por ejemplo, desde un input "nombre")
        if 'nombre' in request.form:
            nombre = request.form.get('nombre', '').upper()
            resultados = RegistroAdultoMayor.query.filter(
                RegistroAdultoMayor.paciente.ilike(f"%{nombre}%")
            ).all()
            return render_template('enfermeria/formulario.html', resultados=resultados, datos=datos, registros=registros)

        # Si el POST es para guardar un registro (ejemplo: campo obligatorio 'paciente')
        validado, campo = campos_validos(request.form)
        if not validado:
            flash(f"Completa el campo: {campo}", 'danger')
            print(f"[VALIDACIÓN] Campo inválido: {campo}")
            datos = request.form
            return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

        try:
            fecha_obj = datetime.strptime(get_str(request.form, 'fecha'), '%Y-%m-%d').date()

            nuevo_registro = RegistroAdultoMayor(
                unidad_salud = get_str(request.form, 'unidad_salud'),
                entidad_federativa = get_str(request.form, 'entidad_federativa'),
                clues = get_str(request.form, 'clues'),
                localidad = get_str(request.form, 'localidad'),
                servicio = get_str(request.form, 'servicio'),
                personal_enfermeria = get_str(request.form, 'personal_enfermeria'),
                fecha = fecha_obj,
                hora_inicio = get_str(request.form, 'hora_inicio'),
                hora_termino = get_str(request.form, 'hora_termino'),
                nombre_jefe_fam = get_str(request.form, 'nombre_jefe_fam').upper(),
                paciente = get_str(request.form, 'paciente').upper(),
                fecha_nacimiento = get_str(request.form, 'fecha_nacimiento'),
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
            db.session.commit()
            flash('Registro guardado exitosamente.', 'success')
            datos = {}  # limpiar formulario después de guardar

        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar: {e}', 'danger')
            datos = request.form
            return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

    # GET o después de guardar muestra formulario limpio con registros
    return render_template('enfermeria/formulario.html', datos=datos, registros=registros)

@bp.route('/guardar', methods=['POST'])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def guardar():
    try:
        nuevo_registro = RegistroAdultoMayor(
            unidad_salud=get_str('unidad_salud'),
            entidad_federativa=get_str('entidad_federativa'),
            clues=get_str('clues'),
            localidad=get_str('localidad'),
            servicio=get_str('servicio'),
            personal_enfermeria=session.get('usuario', '').upper(),
            fecha=get_date('fecha'),
            hora_inicio=request.form.get('hora_inicio', '').strip(),
            hora_termino=request.form.get('hora_termino', '').strip(),
            nombre_jefe_fam=get_str('nombre_jefe_fam'),
            paciente=get_str('paciente'),
            fecha_nacimiento=request.form.get('fecha_nacimiento', '').strip(),
            domicilio=get_str('domicilio'),
            edad=get_int('edad'),
            sexo=get_str('sexo'),
            indigena=get_str('indigena'),
            migrante=get_str('migrante'),
            nivel_atencion=get_str('nivel_atencion'),
            consulta_enfermeria=get_str('consulta_enfermeria'),
            consultoria_otorgada=get_str('consultoria_otorgada'),
            prescripcion_medicamentos=get_str('prescripcion_medicamentos'),
            DG_plan_cuidados=get_str('DG_plan_cuidados'),
            DG_GRUPOS_EDAD=get_str('DG_GRUPOS_EDAD'),
            INSTITUCION_PROCEDENCIA=get_str('INSTITUCION_PROCEDENCIA'),
            CONSEJERIA_PF=get_str('CONSEJERIA_PF'),
            PF_GRUPOS_EDAD=get_str('PF_GRUPOS_EDAD'),
            PF_SUBSECUENTE=get_str('PF_SUBSECUENTE'),
            PF_METODO=get_str('PF_METODO'),
            VI_EMB_grupo_edad=get_str('VI_EMB_grupo_edad'),
            VI_EMB_TRIMESTRE_GESTACIONAL=get_str('VI_EMB_TRIMESTRE_GESTACIONAL'),
            VI_EMB_ACCIONES_IRREDUCTIBLES=get_list_as_str('VI_EMB_ACCIONES_IRREDUCTIBLES[]'),
            observaciones=get_str('observaciones'),
            DETECCION_TAMIZ=get_str('DETECCION_TAMIZ'),
            diagnostico_nutricional=get_str('diagnostico_nutricional'),
            SALUD_GINECO_DETECCION=get_str('SALUD_GINECO_DETECCION'),
            EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS=get_str('EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS'),
            EDA_MADRES_CAPACITADAS_MANEJO=get_str('EDA_MADRES_CAPACITADAS_MANEJO'),
            IRA_MADRES_CAPACITADAS_MANEJO=get_str('IRA_MADRES_CAPACITADAS_MANEJO'),
            grupo_riesgo=get_str('grupo_riesgo'),
            DETECCION_ENFERMEDADES_CRONICAS=get_str('DETECCION_ENFERMEDADES_CRONICAS'),
            DIABETES_MELLITUS=get_str('DIABETES_MELLITUS'),
            DISLIPIDEMIA=get_str('DISLIPIDEMIA'),
            hipertension=get_str('hipertension'),
            REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES=get_str('REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES'),
            DIABETICOS_INFORMADOS_CUIDADOS_PIES=get_str('DIABETICOS_INFORMADOS_CUIDADOS_PIES'),
            vacunacion=get_str('vacunacion'),
            PROMOCION_SALUD=get_str('PROMOCION_SALUD'),
            DERIVACION=get_str('DERIVACION'),
            ACTIVIDADES_ASISTENCIALES=get_str('ACTIVIDADES_ASISTENCIALES'),
            OBSERVACIONES_GENERALES=get_str('OBSERVACIONES_GENERALES'),
        )
        db.session.add(nuevo_registro)
        db.session.commit()
        flash('Registro guardado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al guardar el registro: {e}', 'danger')
    return redirect(url_for('enfermeria.formulario'))

@bp.route('/exportar', methods=['POST'])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def exportar():
    ids = request.form.getlist('ids')
    registros = RegistroAdultoMayor.query.filter(RegistroAdultoMayor.id.in_(ids)).all()
    if not registros:
        flash('No se seleccionaron registros válidos para exportar.', 'warning')
        return redirect(url_for('enfermeria.formulario'))
    data = [{
        'Paciente': r.paciente,
        'Edad': r.edad,
        'Domicilio': r.domicilio,
        'Unidad de Salud': r.unidad_salud,
        'Fecha': r.fecha,
        'Hora de Inicio': r.hora_inicio,
        'Hora de Término': r.hora_termino,
        'Nombre del Jefe de Familia': r.nombre_jefe_fam,
    } for r in registros]
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="registros.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@bp.route('/eliminar', methods=['POST'])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
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
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def consultar():
    resultados = []
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        resultados = RegistroAdultoMayor.query.filter(
            RegistroAdultoMayor.paciente.ilike(f"%{nombre}%")
        ).all()
    return render_template('enfermeria/consulta_nombre.html', resultados=resultados)

@bp.route('/detalle/<int:registro_id>')
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def detalle(registro_id):
    registro = RegistroAdultoMayor.query.get_or_404(registro_id)
    return render_template('enfermeria/detalle.html', registro=registro)

@bp.route('/api/total_capturados_mes', methods=['GET'])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def total_capturados_mes():
    try:
        usua = session.get('usuario')
        if not usua:
            return jsonify({'error': 'Sesión no válida'}), 401
        hoy = datetime.now()
        if hoy.month == 1:
            inicio = datetime(hoy.year - 1, 12, 26)
        else:
            inicio = datetime(hoy.year, hoy.month - 1, 26)
        fin = datetime(hoy.year, hoy.month, 25, 23, 59, 59)
        total = RegistroAdultoMayor.query.filter(
            RegistroAdultoMayor.fecha >= inicio,
            RegistroAdultoMayor.fecha <= fin,
            RegistroAdultoMayor.personal_enfermeria == usua
        ).count()
        return jsonify({'total': total})
    except Exception as e:
        return jsonify({'total': 0, 'error': f'Error al obtener datos: {e}'}), 500

@bp.route("/api/reporte", methods=["GET"])
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
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
@login_required(roles=['UsuarioEnfermeria', 'Administrador', 'SuperUsuario'])
def tutorial():
    if 'usuario' not in session:
        flash('Inicia sesión para acceder al tutorial.', 'warning')
        return redirect(url_for('admin.auth.login'))
    return render_template('enfermeria/tutorial.html')
