# app/models/enfermeria.py
from datetime import date, datetime
from app.utils.db import db
from app.models.personal import Usuario

# Modelo RegistroAdultoMayor
class RegistroAdultoMayor(db.Model):
    __tablename__ = 'registroadultosmayores'

    id = db.Column(db.Integer, primary_key=True)
    unidad_salud = db.Column(db.String)
    entidad_federativa = db.Column(db.String)
    clues = db.Column(db.String)
    localidad = db.Column(db.String)
    servicio = db.Column(db.String)
    personal_enfermeria = db.Column(db.String)
    fecha = db.Column(db.Date)
    hora_inicio = db.Column(db.String)
    hora_termino = db.Column(db.String)
    nombre_jefe_fam = db.Column(db.String)
    paciente = db.Column(db.String)
    fecha_nacimiento = db.Column(db.String)
    domicilio = db.Column(db.String)
    edad = db.Column(db.Integer)
    sexo = db.Column(db.String)
    indigena = db.Column(db.String)
    migrante = db.Column(db.String)
    nivel_atencion = db.Column(db.String)
    consulta_enfermeria = db.Column(db.String)
    consultoria_otorgada = db.Column(db.String)
    prescripcion_medicamentos = db.Column(db.String)
    DG_plan_cuidados = db.Column(db.String)
    DG_GRUPOS_EDAD = db.Column(db.String)
    INSTITUCION_PROCEDENCIA = db.Column(db.String)
    CONSEJERIA_PF = db.Column(db.String)
    PF_GRUPOS_EDAD = db.Column(db.String)
    PF_SUBSECUENTE = db.Column(db.String)
    PF_METODO = db.Column(db.String)
    VI_EMB_grupo_edad = db.Column(db.String)
    VI_EMB_TRIMESTRE_GESTACIONAL = db.Column(db.String)
    VI_EMB_ACCIONES_IRREDUCTIBLES = db.Column(db.String)
    observaciones = db.Column(db.String)
    DETECCION_TAMIZ = db.Column(db.String)
    diagnostico_nutricional = db.Column(db.String)
    SALUD_GINECO_DETECCION = db.Column(db.String)
    EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS = db.Column(db.String)
    EDA_MADRES_CAPACITADAS_MANEJO = db.Column(db.String)
    IRA_MADRES_CAPACITADAS_MANEJO = db.Column(db.String)
    grupo_riesgo = db.Column(db.String)
    DETECCION_ENFERMEDADES_CRONICAS = db.Column(db.String)
    DIABETES_MELLITUS = db.Column(db.String)
    DISLIPIDEMIA = db.Column(db.String)
    hipertension = db.Column(db.String)
    REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES = db.Column(db.String)
    DIABETICOS_INFORMADOS_CUIDADOS_PIES = db.Column(db.String)
    vacunacion = db.Column(db.String)
    PROMOCION_SALUD = db.Column(db.String)
    DERIVACION = db.Column(db.String)
    ACTIVIDADES_ASISTENCIALES = db.Column(db.String)
    OBSERVACIONES_GENERALES = db.Column(db.String)

    def to_dict(self):
        def safe_iso(value):
            if isinstance(value, (date, datetime)):
                return value.isoformat()
            return value

        return {c.name: safe_iso(getattr(self, c.name)) for c in self.__table__.columns}

# Modelo Archivo
class Archivo(db.Model):
    __tablename__ = 'archivos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    nombre_formato = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    fecha_subida = db.Column(db.DateTime, server_default=db.func.now())
