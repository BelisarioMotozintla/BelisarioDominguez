from flask import Blueprint, render_template, request, redirect, url_for, flash,jsonify
from app.models.archivo_clinico import Paciente,UnidadSalud,PacienteUnidad
from app.utils.helpers import login_required
from app import db
from datetime import date

bp = Blueprint('paciente', __name__, template_folder='templates/paciente')

@bp.route('/')
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def listar_pacientes():
    pacientes = Paciente.query.all()
    return render_template('paciente/listar.html', pacientes=pacientes)

@bp.route('/alta', methods=['GET', 'POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def alta_paciente():
    if request.method == 'POST':
        curp = request.form['curp'].strip().upper()

        # Verificar si el CURP ya existe
        existente = Paciente.query.filter_by(curp=curp).first()
        if existente:
            flash('Ya existe un paciente registrado con ese CURP.', 'danger')
            return redirect(url_for('paciente.alta_paciente'))

        # Crear nuevo paciente
        nuevo = Paciente(
            nombre=request.form['nombre'].strip(),
            curp=curp,
            fecha_nacimiento=request.form.get('fecha_nacimiento') or None,
            sexo=request.form['sexo'],
            direccion=request.form.get('direccion'),
            es_cronico=request.form.get('es_cronico', 'No'),
            tipo_cronicidad=request.form.get('tipo_cronicidad') or None,
            esta_embarazada=request.form.get('esta_embarazada', 'No')
        )
        db.session.add(nuevo)
        db.session.flush()  # Obtener ID sin hacer commit aún

        # Datos de unidad y tipo de relación
        id_unidad = request.form.get('id_unidad')
        tipo_relacion = request.form.get('tipo_relacion')
        fecha_relacion = date.today()

        relacion = PacienteUnidad(
            id_paciente=nuevo.id_paciente,
            id_unidad=id_unidad,
            tipo_relacion=tipo_relacion,
            fecha_relacion=fecha_relacion
        )
        db.session.add(relacion)
        db.session.commit()

        flash('Paciente registrado correctamente', 'success')
        return redirect(url_for('paciente.listar_pacientes'))

    # GET: cargar unidades para el formulario
    unidades = UnidadSalud.query.order_by(UnidadSalud.nombre).all()
    return render_template('paciente/alta.html', unidades=unidades)

@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def editar_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    relacion = PacienteUnidad.query.filter_by(id_paciente=paciente.id_paciente).first()
    unidades = UnidadSalud.query.order_by(UnidadSalud.nombre).all()

    if request.method == 'POST':
        # Datos del paciente
        paciente.nombre = request.form['nombre']
        paciente.curp = request.form['curp']
        paciente.fecha_nacimiento = request.form.get('fecha_nacimiento')
        paciente.sexo = request.form['sexo']
        paciente.direccion = request.form.get('direccion')
        paciente.es_cronico = request.form.get('es_cronico', 'No')
        paciente.tipo_cronicidad = request.form.get('tipo_cronicidad') or None
        paciente.esta_embarazada = request.form.get('esta_embarazada', 'No')

        # Datos de relación unidad
        if relacion:
            relacion.id_unidad = request.form.get('id_unidad')
            relacion.tipo_relacion = request.form.get('tipo_relacion')
        else:
            # Si no tenía relación, la crea
            nueva_relacion = PacienteUnidad(
                id_paciente=paciente.id_paciente,
                id_unidad=request.form.get('id_unidad'),
                tipo_relacion=request.form.get('tipo_relacion'),
                fecha_relacion=date.today()
            )
            db.session.add(nueva_relacion)

        db.session.commit()
        flash('Paciente actualizado correctamente', 'success')
        return redirect(url_for('paciente.listar_pacientes'))

    return render_template('paciente/editar.html', paciente=paciente, relacion=relacion, unidades=unidades)

@bp.route('/buscar')
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def buscar_paciente():
    query = request.args.get('query', '').strip()
    resultados = []
    if query:
        resultados = Paciente.query.filter(
            (Paciente.nombre.ilike(f'%{query}%')) |
            (Paciente.curp.ilike(f'%{query}%'))
        ).limit(10).all()

    return jsonify([
        {'id_paciente': p.id_paciente, 'nombre': p.nombre, 'curp': p.curp}
        for p in resultados
    ])

@bp.route('/eliminar/<int:id>', methods=['POST'])
@login_required(roles=['Administrador', 'UsuarioAdministrativo'])
def eliminar_paciente(id):
    paciente = Paciente.query.get_or_404(id)
    db.session.delete(paciente)
    db.session.commit()
    flash('Paciente eliminado correctamente.', 'success')
    return redirect(url_for('paciente.listar_pacientes'))
