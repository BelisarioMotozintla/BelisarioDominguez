from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, IntegerField, DateField, TimeField, SubmitField
from wtforms.validators import Optional, DataRequired
from datetime import datetime
from app.models.personal import Servicio,Usuario, Roles

class NotaConsultaForm(FlaskForm):
    id_servicio = SelectField("Servicio", coerce=int, choices=[], validators=[DataRequired()])
    medico_responsable = SelectField("Médico Responsable", coerce=int, choices=[], validators=[Optional()])  # <-- agregado

    # Fecha y hora
    fecha = DateField("Fecha", default=datetime.utcnow, validators=[Optional()])
    hora = TimeField("Hora", default=lambda: datetime.utcnow().time(), validators=[Optional()])

    # Signos vitales
    peso = DecimalField("Peso", validators=[Optional()])
    talla = DecimalField("Talla", validators=[Optional()])
    imc = DecimalField("IMC", validators=[Optional()])
    ta = StringField("TA", validators=[Optional()])
    fc = IntegerField("FC", validators=[Optional()])
    fr = IntegerField("FR", validators=[Optional()])
    temp = DecimalField("Temperatura", validators=[Optional()])
    cc = DecimalField("CC", validators=[Optional()])
    spo2 = IntegerField("SpO2", validators=[Optional()])
    glicemia = IntegerField("Glicemia", validators=[Optional()])

    # SOAP
    #presentacion = TextAreaField("Presentación", validators=[Optional()]) se elimina por que se duplica
    antecedentes = TextAreaField("S - Subjetivo", validators=[DataRequired()])
    exploracion_fisica = TextAreaField("O - Objetivo", validators=[DataRequired()])
    diagnostico = TextAreaField("A - Análisis", validators=[DataRequired()])
    plan = TextAreaField("P - Plan", validators=[DataRequired()])
    pronostico = TextAreaField("Pronóstico", validators=[DataRequired()])
    laboratorio = TextAreaField("Laboratorio", validators=[Optional()])

    submit = SubmitField("💾 Guardar Nota")

    def __init__(self, es_pasante=False, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Servicios
        try:
            servicios = Servicio.query.filter_by(area='Paciente').all()
            self.id_servicio.choices = [(s.id_servicio, s.nombre_servicio) for s in servicios] or [(0, "No hay servicios disponibles")]
        except Exception as e:
            self.id_servicio.choices = [(0, f"Error cargando servicios: {e}")]

        # Si es pasante -> cargar médicos responsables
        if es_pasante:
            try:
                medicos = Usuario.query.join(nombre_rol).filter(Roles.nombre_rol == "Medico").all()
                self.medico_responsable.choices = [(m.id_usuario, m.usuario) for m in medicos]
            except Exception as e:
                self.medico_responsable.choices = [(0, f"Error cargando médicos: {e}")]
        else:
            # No es pasante → no necesita este campo
            self.medico_responsable.choices = []
