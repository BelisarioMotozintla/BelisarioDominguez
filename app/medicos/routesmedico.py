from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from flask_login import login_required, current_user
from your_app import db
from your_app.models import NotaConsultaExterna, Paciente, ExpedienteClinico, Usuario
from your_app.forms import NotaConsultaForm
from datetime import datetime
import io
# Para generar PDF con WeasyPrint:
from weasyprint import HTML

archivo_clinico_bp = Blueprint('archivo_clinico', __name__, url_prefix='/archivo_clinico')

@archivo_clinico_bp.route('/notas')
@login_required
def listar_notas():
    notas = NotaConsultaExterna.query.order_by(NotaConsultaExterna.fecha.desc()).all()
    return render_template('archivo_clinico/listar_notas.html', notas=notas)

@archivo_clinico_bp.route('/nota/nueva', methods=['GET', 'POST'])
@login_required
def nueva_nota():
    form = NotaConsultaForm()
    # cargar choices
    form.id_paciente.choices = [(p.id, f"{p.apellido_paterno} {p.nombre}") for p in Paciente.query.order_by(Paciente.apellido_paterno).all()]
    expedientes = ExpedienteClinico.query.all()
    form.id_expediente.choices = [(e.id, f"{e.id} - {e.descripcion[:40]}") for e in expedientes]
    form.id_expediente.choices.insert(0, (0, ' -- Ninguno -- '))

    if form.validate_on_submit():
        id_expediente = form.id_expediente.data or None
        if id_expediente == 0:
            id_expediente = None

        nota = NotaConsultaExterna(
            id_paciente=form.id_paciente.data,
            id_expediente=id_expediente,
            id_usuario=current_user.id,
            fecha=form.fecha.data,
            hora=form.hora.data,
            peso=form.peso.data,
            talla=form.talla.data,
            ta=form.ta.data,
            fc=form.fc.data,
            fr=form.fr.data,
            temp=form.temp.data,
            cc=form.cc.data,
            spo2=form.spo2.data,
            glicemia=form.glicemia.data,
            imc=form.imc.data,
            antecedentes=form.antecedentes.data,
            exploracion_fisica=form.exploracion_fisica.data,
            diagnostico=form.diagnostico.data,
            plan=form.plan.data,
            pronostico=form.pronostico.data,
            laboratorio=form.laboratorio.data,
        )
        db.session.add(nota)
        db.session.commit()
        flash('Nota registrada correctamente', 'success')
        return redirect(url_for('archivo_clinico.ver_nota', id_nota=nota.id_nota))

    # default fecha a hoy
    if request.method == 'GET' and not form.fecha.data:
        form.fecha.data = datetime.utcnow().date()

    return render_template('archivo_clinico/nueva_nota.html', form=form)

@archivo_clinico_bp.route('/nota/<int:id_nota>')
@login_required
def ver_nota(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    return render_template('archivo_clinico/ver_nota.html', nota=nota)

@archivo_clinico_bp.route('/nota/<int:id_nota>/pdf')
@login_required
def nota_pdf(id_nota):
    nota = NotaConsultaExterna.query.get_or_404(id_nota)
    html = render_template('archivo_clinico/nota_pdf.html', nota=nota)
    # Generar PDF con WeasyPrint
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf),
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'nota_{nota.id_nota}.pdf')
