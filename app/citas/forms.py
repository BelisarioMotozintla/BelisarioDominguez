from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, IntegerField, SubmitField
from wtforms.validators import DataRequired

class ProgramarCitaForm(FlaskForm):
    fecha_hora = DateTimeLocalField("Fecha y hora", format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    duracion_min = IntegerField("Duración (min)", default=30)
    submit = SubmitField("Programar cita")
