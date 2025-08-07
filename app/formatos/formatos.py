from flask import Blueprint, current_app, render_template, request, redirect, send_from_directory, session, flash, url_for
import os
from werkzeug.utils import secure_filename
from app.utils.helpers import allowed_file, login_required 
from app.utils.db import db
from app.models.enfermeria import Archivo
#from app.utils.auth import login_required  # Asegúrate de que esté importado correctamente
from . import formatos_bp as bp


@bp.route('/', methods=['GET', 'POST'])
@login_required()
def formatos():
    archivos = Archivo.query.order_by(Archivo.fecha_subida.desc()).all()
    return render_template(
        'formatos/index.html',
        archivos=archivos,
        usuario=session['usuario'],
        rol=session.get('rol'),
        es_admin=(session['rol'] in ['admin', 'Administrador'])
    )


@bp.route('/upload', methods=['POST'])
@login_required(roles=['SuperUsuario'])
def upload():
    file = request.files.get('file')
    nombre_formato = request.form.get('nombre_formato')
    area = request.form.get('area')

    if not file or not nombre_formato or not area:
        flash('Todos los campos son obligatorios.', 'warning')
        return redirect(url_for('formatos.formatos'))

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads'))
        os.makedirs(upload_folder, exist_ok=True)

        file.save(os.path.join(upload_folder, filename))

        nuevo_archivo = Archivo(
            filename=filename,
            nombre_formato=nombre_formato,
            area=area
        )
        db.session.add(nuevo_archivo)
        db.session.commit()

        flash('Archivo subido correctamente.', 'success')
    else:
        flash('Tipo de archivo no permitido.', 'danger')

    return redirect(url_for('formatos.formatos'))


@bp.route('/download/<filename>')
@login_required(roles=['UsuarioEnfermeria', 'UsuarioAdministrativo'])
def download_file(filename):
    try:
        filename = secure_filename(filename)
        upload_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads'))
        file_path = os.path.join(upload_folder, filename)

        archivo = Archivo.query.filter_by(filename=filename).first()
        if not archivo:
            flash('Archivo no encontrado en la base de datos.', 'warning')
            return redirect(url_for('formatos.formatos'))

        if not os.path.exists(file_path):
            flash('Archivo no disponible en el servidor.', 'warning')
            return redirect(url_for('formatos.formatos'))

        return send_from_directory(upload_folder, filename, as_attachment=True)

    except Exception as e:
        current_app.logger.error(f"Error al descargar el archivo {filename}: {str(e)}")
        flash('Error al descargar el archivo.', 'danger')
        return redirect(url_for('formatos.formatos'))


@bp.route('/delete/<int:file_id>', methods=['POST'])
@login_required(roles=['SuperUsuario'])
def delete_file(file_id):
    try:
        archivo = Archivo.query.get(file_id)
        if not archivo:
            flash('Archivo no encontrado.', 'warning')
            return redirect(url_for('formatos.formatos'))

        upload_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'static', 'uploads'))
        file_path = os.path.join(upload_folder, archivo.filename)

        if os.path.exists(file_path):
            os.remove(file_path)

        db.session.delete(archivo)
        db.session.commit()
        flash('Archivo eliminado correctamente.', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar el archivo {file_id}: {str(e)}")
        flash('Error al eliminar el archivo.', 'danger')

    return redirect(url_for('formatos.formatos'))
