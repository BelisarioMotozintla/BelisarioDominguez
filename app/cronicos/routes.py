from datetime import date,datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for,jsonify,send_file
from app.utils.db import db
from app.models.archivo_clinico import Paciente, ArchivoClinico
from app.models.medicos import  ControlClinico, Laboratorio, SignosVitales, PieDiabetico, DiagnosticoPaciente, TratamientoFarmacologico,MedicamentoTratamiento
from app.models.farmacia import Diagnostico,Medicamento
from app.utils.helpers import usuarios_con_rol_requerido,roles_required  # tu decorador para control de acceso
from sqlalchemy import or_
from sqlalchemy import func,cast, String
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from io import BytesIO




bp = Blueprint("cronicos", __name__, template_folder="templates")

# 🔹 LISTA DE PACIENTES CRÓNICOS

@bp.route("/pacientes", methods=["GET", "POST"])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def pacientes_cronicos():
    query = request.args.get('q', '').strip()

    # Usamos selectinload para evitar muchas consultas SQL
    archivos = (
        ArchivoClinico.query
        .options(joinedload(ArchivoClinico.paciente))
    )

    if query:
        archivos = archivos.join(Paciente).filter(
            (Paciente.nombre.ilike(f"%{query}%")) |
            (cast(ArchivoClinico.numero_expediente, String).ilike(f"%{query}%")) |
            (Paciente.curp.ilike(f"%{query}%"))     # 🔹 Agregamos CURP también
        )

    pacientes = (
        archivos.order_by(ArchivoClinico.fecha_creacion.desc())
        .limit(10)
        .all()
    )

    return render_template("pacientes_cronicos.html", pacientes=pacientes, buscar=query)

@bp.route("/api/cie10")
def api_cie10():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    dx = Diagnostico.query.filter(
        (Diagnostico.codigo.ilike(f"%{q}%")) |
        (Diagnostico.descripcion.ilike(f"%{q}%"))
    ).limit(20)

    return jsonify([
        {"id": d.id_diagnostico, "text": f"{d.codigo} — {d.descripcion}"}
        for d in dx
    ])

# 🔹 NUEVO CONTROL CLÍNICO
@bp.route("/paciente/<int:id_paciente>/nuevo_control", methods=["GET", "POST"])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def nuevo_control(id_paciente):
    def bad(msg, category="warning"):
        flash(msg, category)
        return redirect(url_for("cronicos.nuevo_control", id_paciente=id_paciente))

    if request.method == "POST":
        # ---------- 1) DIAGNÓSTICO ----------
        id_dx_raw = request.form.get("id_diagnostico")
        if not id_dx_raw:
            return bad("Seleccione un diagnóstico CIE-10.", "warning")
        try:
            id_dx_int = int(id_dx_raw)
        except ValueError:
            return bad("Diagnóstico inválido.", "danger")
        dx_catalogo = Diagnostico.query.get(id_dx_int)
        if not dx_catalogo:
            return bad("El diagnóstico no existe en el catálogo CIE-10.", "danger")

        # ---------- 2) FECHA DEL CONTROL ----------
        fecha_control_raw = request.form.get("fecha_control")
        if not fecha_control_raw:
            return bad("Debe ingresar la fecha del control.", "warning")
        try:
            fecha_control = datetime.strptime(fecha_control_raw, "%Y-%m-%d").date()
        except Exception:
            return bad("Formato de fecha inválido.", "warning")

        # ---------- 3) SIGNOS VITALES (validaciones y cálculo IMC) ----------
        peso_raw = request.form.get("peso")
        talla_raw = request.form.get("talla")
        ps_raw = request.form.get("ps")
        pd_raw = request.form.get("pd")
        cintura_raw = request.form.get("cintura")

        # Normalizar empty->None
        peso = float(peso_raw) if peso_raw and peso_raw.strip() != "" else None
        talla = float(talla_raw) if talla_raw and talla_raw.strip() != "" else None
        ps = int(ps_raw) if ps_raw and ps_raw.strip() != "" else None
        pd = int(pd_raw) if pd_raw and pd_raw.strip() != "" else None
        cintura = float(cintura_raw) if cintura_raw and cintura_raw.strip() != "" else None

        # Reglas:
        # peso & talla deben ir juntos si uno de los dos se provee
        if (peso is not None and talla is None) or (talla is not None and peso is None):
            return bad("Para calcular IMC debe ingresar peso y talla.", "warning")

        if peso is not None and not (20 <= peso <= 350):
            return bad("El peso debe estar entre 20 y 350 kg.", "warning")
        if talla is not None and not (80 <= talla <= 230):
            return bad("La talla debe estar entre 80 y 230 cm.", "warning")

        imc = None
        if peso is not None and talla is not None:
            try:
                imc = round(peso / ((talla / 100) ** 2), 2)
            except Exception:
                imc = None

        # Presiones: si uno está presente, el otro debe estarlo
        if (ps is not None and pd is None) or (pd is not None and ps is None):
            return bad("Debe ingresar presión sistólica y diastólica.", "warning")
        if ps is not None and not (70 <= ps <= 260):
            return bad("La presión sistólica debe estar entre 70 y 260.", "warning")
        if pd is not None and not (40 <= pd <= 150):
            return bad("La presión diastólica debe estar entre 40 y 150.", "warning")

        # ---------- 4) LABORATORIO (validaciones opcionales) ----------
        def parse_number(name):
            raw = request.form.get(name)
            return float(raw) if raw and raw.strip() != "" else None

        glucosa = parse_number("glucosa")
        colesterol = parse_number("colesterol")
        hdl = parse_number("hdl")
        ldl = parse_number("ldl")
        trigliceridos = parse_number("trigliceridos")
        hba1c = parse_number("hba1c")
        microalbumina = parse_number("microalbumina")

        if glucosa is not None and not (40 <= glucosa <= 600):
            return bad("La glucosa debe estar entre 40 y 600 mg/dL.", "warning")
        if colesterol is not None and not (70 <= colesterol <= 500):
            return bad("El colesterol debe estar entre 70 y 500 mg/dL.", "warning")
        # rangos opcionales para otros valores (ajusta si lo deseas)
        if hba1c is not None and not (2 <= hba1c <= 20):
            return bad("HbA1c fuera de rango esperado.", "warning")

        # ---------- 5) PIE DIABÉTICO ----------
        clasificacion_pie = request.form.get("clasificacion_pie")
        if not clasificacion_pie and clasificacion_pie != "0":
            return bad("Debe seleccionar la clasificación de pie diabético.", "warning")

        observaciones = request.form.get("obs") or None

        # ---------- 6) VALIDAR MEDICAMENTOS ----------
        ids_meds = request.form.getlist("id_medicamento[]")
        dosis_list = request.form.getlist("dosis[]")
        frecuencia_list = request.form.getlist("frecuencia[]")
        inicio_list = request.form.getlist("fecha_inicio[]")
        fin_list = request.form.getlist("fecha_fin[]")

        # Si hay medicamentos, cada uno debe tener dosis, frecuencia e inicio; fin opcional pero si existe debe ser >= inicio
        for i, mid_raw in enumerate(ids_meds):
            if not mid_raw or mid_raw.strip() == "":
                continue  # salto vacíos (posible clon sin seleccionar)
            # validar id medicamento entero
            try:
                _mid = int(mid_raw)
            except ValueError:
                return bad(f"ID de medicamento inválido en la fila {i+1}.", "warning")

            dosis_val = (dosis_list[i] if i < len(dosis_list) else "") or ""
            frec_val = (frecuencia_list[i] if i < len(frecuencia_list) else "") or ""
            inicio_val = (inicio_list[i] if i < len(inicio_list) else "") or ""
            fin_val = (fin_list[i] if i < len(fin_list) else "") or ""

            if dosis_val.strip() == "" or frec_val.strip() == "" or inicio_val.strip() == "":
                return bad(f"El medicamento en la fila {i+1} necesita dosis, frecuencia y fecha de inicio.", "warning")

            # validar fechas
            try:
                fecha_inicio_med = datetime.strptime(inicio_val, "%Y-%m-%d").date()
            except Exception:
                return bad(f"Fecha de inicio inválida en el medicamento fila {i+1}.", "warning")

            fecha_fin_med = None
            if fin_val.strip() != "":
                try:
                    fecha_fin_med = datetime.strptime(fin_val, "%Y-%m-%d").date()
                except Exception:
                    return bad(f"Fecha fin inválida en el medicamento fila {i+1}.", "warning")
                if fecha_fin_med < fecha_inicio_med:
                    return bad(f"La fecha fin no puede ser menor que la fecha inicio (medicamento fila {i+1}).", "warning")

        # ---------- 7) GUARDAR EN DB (si todo pasó) ----------
        try:
            control = ControlClinico(
                id_paciente=id_paciente,
                fecha_control=fecha_control
            )
            db.session.add(control)
            db.session.flush()  # para obtener id_control

            # SignosVitales
            signos = SignosVitales(
                id_control=control.id_control,
                peso=peso,
                talla=talla,
                cintura=cintura,
                presion_sistolica=ps,
                presion_diastolica=pd,
                imc=imc
            )
            db.session.add(signos)

            # Laboratorio
            laboratorio = Laboratorio(
                id_control=control.id_control,
                glucosa=glucosa,
                colesterol_total=colesterol,
                hdl=hdl,
                ldl=ldl,
                trigliceridos=trigliceridos,
                hba1c=hba1c,
                microalbumina=microalbumina
            )
            db.session.add(laboratorio)

            # Pie diabetico
            pie = PieDiabetico(
                id_control=control.id_control,
                clasificacion_pie=clasificacion_pie,
                observaciones=observaciones
            )
            db.session.add(pie)

            # DiagnósticoPaciente
            dx_paciente = DiagnosticoPaciente(
                id_paciente=id_paciente,
                id_diagnostico=id_dx_int,
                id_control=control.id_control,
                fecha=fecha_control
            )
            db.session.add(dx_paciente)
            db.session.flush()

            # Tratamiento y Medicamentos
            tratamiento = TratamientoFarmacologico(id_dx=dx_paciente.id)
            db.session.add(tratamiento)
            db.session.flush()

            for i, mid_raw in enumerate(ids_meds):
                if not mid_raw or mid_raw.strip() == "":
                    continue
                mid = int(mid_raw)
                dosis_val = (dosis_list[i] if i < len(dosis_list) else None) or None
                frec_val = (frecuencia_list[i] if i < len(frecuencia_list) else None) or None
                inicio_val = (inicio_list[i] if i < len(inicio_list) else None) or None
                fin_val = (fin_list[i] if i < len(fin_list) else None) or None

                med_trat = MedicamentoTratamiento(
                    id_tratamiento=tratamiento.id_tratamiento,
                    id_medicamento=mid,
                    dosis=dosis_val,
                    frecuencia=frec_val,
                    fecha_inicio=inicio_val,
                    fecha_fin=fin_val
                )
                db.session.add(med_trat)

            db.session.commit()
            flash("Control clínico registrado correctamente.", "success")
            return redirect(url_for("cronicos.detalle_control", id_control=control.id_control))

        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Error guardando control clínico:")
            flash("Error al guardar el control. Intente nuevamente.", "danger")
            return redirect(url_for("cronicos.nuevo_control", id_paciente=id_paciente))

    # GET -> render
    diagnosticos = Diagnostico.query.order_by(Diagnostico.codigo).all()
    medicamentos = Medicamento.query.order_by(Medicamento.nombre_comercial).all()

    return render_template(
    "nuevo_control.html",
    id_paciente=id_paciente,
    diagnosticos=diagnosticos,
    medicamentos=medicamentos,
    form=request.form
    )



# 🔹 VER DETALLE COMPLETO DEL CONTROL (JOIN)
@bp.route("/controles/<int:id_paciente>")
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def lista_controles(id_paciente):
    controles = ControlClinico.query.filter_by(id_paciente=id_paciente).all()
    paciente = Paciente.query.get_or_404(id_paciente)
    return render_template("lista_controles.html", controles=controles, paciente=paciente)

@bp.route('/eliminar_control/<int:id_control>', methods=['GET', 'POST'])
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def eliminar_control(id_control):
    control = ControlClinico.query.get_or_404(id_control)
    id_paciente = control.id_paciente

    db.session.delete(control)
    db.session.commit()
    flash('Control eliminado', 'success')

    return redirect(url_for('cronicos.lista_controles', id_paciente=id_paciente))

# Función para clasificar IMC
def clasificar_imc(imc):
    if imc is None:
        return ("Sin datos", "secondary")
    if imc < 18.5:
        return ("Bajo peso", "warning")
    elif imc < 25:
        return ("Normal", "success")
    elif imc < 30:
        return ("Sobrepeso", "warning")
    else:
        return ("Obesidad", "danger")

# Función para clasificar glucosa
def clasificar_glucosa(glucosa):
    if glucosa is None:
        return ("Sin datos", "secondary")
    if glucosa < 100:
        return ("Normal", "success")
    elif glucosa < 126:
        return ("Prediabetes", "warning")
    else:
        return ("Diabetes", "danger")


# VISTA DETALLE CONTROL

MAPA_CLASIFICACION = {
    "0": "0 = Sin lesión",
    "1": "1 = Úlcera superficial",
    "2": "2 = Úlcera profunda",
    "3": "3 = Infección",
    "4": "4 = Gangrena localizada",
    "5": "5 = Gangrena extensa"
}



@bp.route("/control/<int:id_control>")
@roles_required(['UsuarioEnfermeria', 'Administrador','JefeEnfermeria'])
def detalle_control(id_control):
    control = ControlClinico.query.get_or_404(id_control)

    diagnosticos = control.diagnosticos
    tratamientos = [dx.tratamientos for dx in diagnosticos]

    imc_texto, imc_color = clasificar_imc(control.signos_vitales.imc)
    glucosa_texto, glucosa_color = clasificar_glucosa(control.laboratorio.glucosa)

    return render_template("detalle_control.html",
                           control=control,
                           diagnosticos=diagnosticos,
                           MAPA_CLASIFICACION=MAPA_CLASIFICACION,
                           imc_texto=imc_texto,
                           imc_color=imc_color,
                           glucosa_texto=glucosa_texto,
                           glucosa_color=glucosa_color)




@bp.route("/reporte_excel", methods=["POST"])
def generar_reporte_excel():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin    = request.form.get("fecha_fin")
    # Convertir a date
   # fecha_inicio = pd.to_datetime(fecha_inicio).date()
   # fecha_fin    = pd.to_datetime(fecha_fin).date()
    # Validar que existan
    if not fecha_inicio or not fecha_fin:
        return "Error: Debes seleccionar ambas fechas", 400

    # Convertir a datetime.date
    try:
        fecha_inicio = pd.to_datetime(fecha_inicio).date()
        fecha_fin    = pd.to_datetime(fecha_fin).date()
    except Exception:
        return "Error al convertir fechas", 400

    # Consulta eficiente con JOINS
    registros = (
        db.session.query(DiagnosticoPaciente)
        .options(
            joinedload(DiagnosticoPaciente.paciente),
            joinedload(DiagnosticoPaciente.control)
                .joinedload(ControlClinico.laboratorio),
            joinedload(DiagnosticoPaciente.control)
                .joinedload(ControlClinico.signos_vitales),
            joinedload(DiagnosticoPaciente.control)
                .joinedload(ControlClinico.pie_diabetico),
            joinedload(DiagnosticoPaciente.tratamientos)
                .joinedload(TratamientoFarmacologico.medicamentos)
                .joinedload(MedicamentoTratamiento.medicamento)
        )
        .filter(
            DiagnosticoPaciente.fecha >= fecha_inicio,
            DiagnosticoPaciente.fecha <= fecha_fin
        )
        .all()
    )

    # Convertir a lista de diccionarios para DataFrame
    data = []

    for r in registros:

        for tto in r.tratamientos:
            for med in tto.medicamentos:

                data.append({
                    "ID Paciente": r.paciente.id_paciente,
                    "Paciente": r.paciente.nombre,
                    "Edad": calcular_edad(r.paciente.fecha_nacimiento),
                    "Fecha_Nacimiento": r.paciente.fecha_nacimiento,
                    "CURP":r.paciente.curp,
                    "Genero": r.paciente.sexo,

                    "Localidad":r.paciente.direccion,
                    "Municipio": "Motozintla",
                    "Adscripcion": "CSIMB005343",
                    "Diagnóstico": r.diagnostico_info.descripcion,
                    #"Fecha Diagnóstico": r.fecha,
                    "Medicamento": med.medicamento.nombre_comercial,
                    " ":" ",
                    "Fecha Control": r.control.fecha_control,

                    # Medicamentos
                    
                    #"Dosis": med.dosis,
                    #"Frecuencia": med.frecuencia,
                    #"Inicio medicamento": med.fecha_inicio,
                    #"Fin medicamento": med.fecha_fin,

                    # Laboratorio (completo)
                    "Glucosa": r.control.laboratorio.glucosa if r.control.laboratorio else None,
                    "Colesterol": r.control.laboratorio.colesterol_total if r.control.laboratorio else None,
                    "HDL": r.control.laboratorio.hdl if r.control.laboratorio else None,
                    "LDL": r.control.laboratorio.ldl if r.control.laboratorio else None,
                    "Triglicéridos": r.control.laboratorio.trigliceridos if r.control.laboratorio else None,
                    "HbA1c": r.control.laboratorio.hba1c if r.control.laboratorio else None,
                    "Microalbumina": r.control.laboratorio.microalbumina if r.control.laboratorio else None,

                    # Signos vitales (completo)
                    "Peso": r.control.signos_vitales.peso if r.control.signos_vitales else None,
                    "Talla": r.control.signos_vitales.talla if r.control.signos_vitales else None,
                    "IMC": r.control.signos_vitales.imc if r.control.signos_vitales else None,
                    "Cintura (C.C.)": r.control.signos_vitales.cintura if r.control.signos_vitales else None,
                    "TA": f"{r.control.signos_vitales.presion_sistolica}/{r.control.signos_vitales.presion_diastolica}"
                        if r.control.signos_vitales else None,

                    # Pie diabético
                    "Clasificación Pie": r.control.pie_diabetico.clasificacion_pie if r.control.pie_diabetico else None,

                })

    # Crear DataFrame
    df = pd.DataFrame(data)

    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")

    output.seek(0)

    return send_file(
        output,
        download_name="reporte_clinico.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
def calcular_edad(fecha_nac):
    if not fecha_nac:
        return None
    hoy = date.today()
    return hoy.year - fecha_nac.year - (
        (hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day)
    )
