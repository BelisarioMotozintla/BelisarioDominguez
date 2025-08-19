from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, TextAreaField, DateField, TimeField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange

class NotaConsultaForm(FlaskForm):
    id_paciente = HiddenField(validators=[DataRequired()])
    id_expediente = HiddenField()

    fecha = DateField('Fecha', validators=[DataRequired()])
    hora = TimeField('Hora', validators=[Optional()])

    peso = DecimalField('Peso (kg)', places=2, validators=[Optional(), NumberRange(min=0)])
    talla = DecimalField('Talla (m)', places=2, validators=[Optional(), NumberRange(min=0)])
    imc = DecimalField('IMC', places=2, validators=[Optional()])

    ta = StringField('Tensión arterial', validators=[Optional()])
    fc = IntegerField('Frecuencia cardíaca (FC)', validators=[Optional(), NumberRange(min=0)])
    fr = IntegerField('Frecuencia respiratoria (FR)', validators=[Optional(), NumberRange(min=0)])
    temp = DecimalField('Temperatura (°C)', places=1, validators=[Optional(), NumberRange(min=0)])
    spo2 = IntegerField('Saturación (SpO2)', validators=[Optional(), NumberRange(min=0)])
    glicemia = IntegerField('Glicemia', validators=[Optional(), NumberRange(min=0)])
    cc = StringField('C.C.', validators=[Optional()])

    antecedentes = TextAreaField('("O-(Objetivo) Lo que el médico observa y mide (signos vitales, exploración física, resultados de estudios).")', validators=[DataRequired()])
    exploracion_fisica = TextAreaField('Exploración física', validators=[DataRequired()])
    diagnostico = TextAreaField('Diagnóstico', validators=[DataRequired()])
    plan = TextAreaField('Plan', validators=[DataRequired()])
    pronostico = TextAreaField('Pronóstico', validators=[DataRequired()])
    laboratorio = TextAreaField('Laboratorio', validators=[Optional()])

    submit = SubmitField('Guardar')
