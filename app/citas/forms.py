from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TimeField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ProgramarCitaForm(FlaskForm):
    consultorio_id = SelectField("Consultorio", coerce=int, validators=[DataRequired()])
    fecha = DateField("Fecha", validators=[DataRequired()])
    hora = TimeField("Hora", validators=[DataRequired()])
    duracion_min = IntegerField(
        "Duración (minutos)",
        validators=[DataRequired(), NumberRange(min=5, max=180)]
    )
    submit = SubmitField("Programar Cita")