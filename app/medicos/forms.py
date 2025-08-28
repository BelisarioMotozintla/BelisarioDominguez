from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, IntegerField, DateField, TimeField, SubmitField
from wtforms.validators import Optional, DataRequired

class NotaConsultaForm(FlaskForm):
   #id_consulta = SelectField("Consulta", coerce=int, validators=[DataRequired()])
    id_servicio = SelectField("Servicio", coerce=int, choices=[], validators=[DataRequired()])
    

    # Fecha y hora
    fecha = DateField("Fecha", default=datetime.utcnow, validators=[Optional()])
    hora = TimeField("Hora", default=lambda: datetime.utcnow().time(), validators=[Optional()])

    # Signos vitales
    peso = DecimalField("Peso", validators=[Optional()])
    talla = DecimalField("Talla", validators=[Optional()])
    ta = StringField("TA", validators=[Optional()])
    fc = IntegerField("FC", validators=[Optional()])
    fr = IntegerField("FR", validators=[Optional()])
    temp = DecimalField("Temperatura", validators=[Optional()])
    cc = DecimalField("CC", validators=[Optional()])
    spo2 = IntegerField("SpO2", validators=[Optional()])
    glicemia = IntegerField("Glicemia", validators=[Optional()])
    imc = DecimalField("IMC", validators=[Optional()])

    # SOAP separado
    presentacion = TextAreaField("Presentación", validators=[Optional()])
    antecedentes = TextAreaField(
        'S-(Subjetivo) Lo que el paciente refiere (síntomas, motivo de consulta, antecedentes relevantes).',
        validators=[DataRequired()]
    )
    exploracion_fisica = TextAreaField(
        'O-(Objetivo) Lo que el médico observa y mide (signos vitales, exploración física, resultados de estudios).',
        validators=[DataRequired()]
    )
    diagnostico = TextAreaField(
        'A-(Análisis) Impresión diagnóstica, diagnósticos diferenciales.',
        validators=[DataRequired()]
    )
    plan = TextAreaField(
        'P-(Plan) Conducta a seguir: estudios, tratamientos, interconsultas, seguimiento.',
        validators=[DataRequired()]
    )
    pronostico = TextAreaField(
        'Pronóstico: Predicción o estimación sobre la evolución y desenlace de la enfermedad de un paciente.',
        validators=[DataRequired()]
    )
    laboratorio = TextAreaField(
        'Resultados de estudios de laboratorio o gabinete.',
        validators=[Optional()]
    )

    submit = SubmitField("💾 Guardar Nota")

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            servicios = Servicio.query.filter_by(area='Paciente').all()
            if servicios:
                self.id_servicio.choices = [(s.id_servicio, s.nombre_servicio) for s in servicios]
            else:
                # placeholder si no hay servicios
                self.id_servicio.choices = [(0, "No hay servicios disponibles")]
        except Exception as e:
            # fallback si falla la query
            self.id_servicio.choices = [(0, f"Error cargando servicios: {e}")]