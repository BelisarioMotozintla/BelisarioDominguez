from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from app.utils.helpers import login_required
from app.models.archivo_clinico import ArchivoClinico
from app.models.personal import Usuario
from app import db
from datetime import datetime

bp = Blueprint('medicos', __name__, template_folder='templates')


@bp.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('auth.login'))


@bp.route('/')
@login_required(roles=['UsuarioAdministrativo', 'Administrador'])
def index():
    registros = ArchivoClinico.query.all()
    return render_template('medicos/index.html', registros=registros)


@bp.route('/dashboard')
@login_required(roles=['UsuarioAdministrativo', 'Administrador'])
def dashboard():
    return render_template('medicos/dashboard.html')


@bp.route('/agregar', methods=['GET', 'POST'])
@login_required(roles=['UsuarioAdministrativo', 'Administrador'])
def agregar():
    if request.method == 'POST':
        try:
            nuevo = ArchivoClinico(
                nombre_paciente=request.form.get('nombre'),
                curp=request.form.get('curp'),
                edad=int(request.form.get('edad', 0)),
                sexo=request.form.get('sexo'),
                motivo_consulta=request.form.get('motivo'),
                antecedentes=request.form.get('antecedentes'),
                diagnostico=request.form.get('diagnostico'),
                tratamiento=request.form.get('tratamiento'),
                fecha_consulta=datetime.strptime(request.form.get('fecha'), '%Y-%m-%d').date()
            )
            db.session.add(nuevo)
            db.session.commit()
            flash('Registro clínico guardado correctamente.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al guardar el registro: {str(e)}', 'danger')
        return redirect(url_for('archivo_clinico.index'))

    return render_template('medicos/agregar.html')
