from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, DateField, TimeField, SubmitField, SelectField
from wtforms.validators import DataRequired, Optional

class NotaConsultaForm(FlaskForm):
    id_paciente = SelectField('Paciente', coerce=int, validators=[DataRequired()])
    id_expediente = SelectField('Expediente (opcional)', coerce=int, validators=[Optional()])
    fecha = DateField('Fecha', validators=[DataRequired()])
    hora = TimeField('Hora', validators=[Optional()])

    peso = DecimalField('Peso (kg)', places=2, validators=[Optional()])
    talla = DecimalField('Talla (m)', places=2, validators=[Optional()])
    ta = StringField('Tensión arterial', validators=[Optional()])
    fc = IntegerField('FC', validators=[Optional()])
    fr = IntegerField('FR', validators=[Optional()])
    temp = DecimalField('Temp (°C)', places=1, validators=[Optional()])
    cc = StringField('C.C.', validators=[Optional()])
    spo2 = IntegerField('SpO2', validators=[Optional()])
    glicemia = IntegerField('Glicemia', validators=[Optional()])
    imc = DecimalField('IMC', places=2, validators=[Optional()])

    antecedentes = TextAreaField('Antecedentes', validators=[Optional()])
    exploracion_fisica = TextAreaField('Exploración física', validators=[Optional()])
    diagnostico = TextAreaField('Diagnóstico', validators=[Optional()])
    plan = TextAreaField('Plan', validators=[Optional()])
    pronostico = TextAreaField('Pronóstico', validators=[Optional()])
    laboratorio = TextAreaField('Laboratorio', validators=[Optional()])

    submit = SubmitField('Guardar')
