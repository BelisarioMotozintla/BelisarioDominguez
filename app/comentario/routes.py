from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models.personal import Usuario
from app.models.comentario import Comentario
from app.utils.db import db
from app.utils.helpers import login_required  # tu decorador para control de acceso

bp = Blueprint('comentario', __name__)

@bp.route('/comentario', methods=['GET', 'POST'])
@login_required(roles=['Usuario', 'Administrador'])
def comentarios():
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(usuario=session['usuario']).first()
        if not usuario:
            flash('Usuario no válido', 'danger')
            return redirect(url_for('auth.login'))

        autor = usuario.empleado.nombre if usuario.empleado else usuario.usuario
        contenido = request.form['contenido']

        nuevo_comentario = Comentario(autor=autor, contenido=contenido)
        db.session.add(nuevo_comentario)
        db.session.commit()

        flash('Comentario agregado correctamente', 'success')
        return redirect(url_for('comentario.comentarios'))

    comentarios = Comentario.query.order_by(Comentario.fecha.desc()).all()
    return render_template('comentario/comentarios.html', comentarios=comentarios)

@bp.route('/comentario/eliminar/<int:id>', methods=['POST'])
@login_required(roles='Administrador')
def eliminar_comentario(id):
    comentario = Comentario.query.get_or_404(id)
    db.session.delete(comentario)
    db.session.commit()
    flash('Comentario eliminado', 'success')
    return redirect(url_for('comentario.comentarios'))
