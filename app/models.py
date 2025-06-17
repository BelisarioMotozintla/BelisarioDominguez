# app/models.py
from datetime import date, datetime
from app.utils.db import db
from werkzeug.security import generate_password_hash, check_password_hash
# Modelo Usuario

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(100), unique=True, nullable=False)
    contrasena = db.Column(db.String(500), nullable=False)
    rol = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.contrasena = generate_password_hash(password)  # Sin .encode()

    def check_password(self, password):
        return check_password_hash(self.contrasena, password)

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
    fecha = db.Column(db.Date)  # o DateTime si usas hora
    hora_inicio = db.Column(db.String)
    hora_termino = db.Column(db.String)
    nombre_jefe_fam = db.Column(db.String)
    paciente = db.Column(db.String)
    fecha_nacimiento = db.Column(db.String)  # o Date si tienes fechas
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
            return value  # Si ya es str u otro tipo, lo deja igual

        return {
            'id': self.id,
            'unidad_salud': self.unidad_salud,
            'entidad_federativa': self.entidad_federativa,
            'clues': self.clues,
            'localidad': self.localidad,
            'servicio': self.servicio,
            'personal_enfermeria': self.personal_enfermeria,
            'fecha': safe_iso(self.fecha),
            'hora_inicio': self.hora_inicio,
            'hora_termino': self.hora_termino,
            'nombre_jefe_fam': self.nombre_jefe_fam,
            'paciente': self.paciente,
            'fecha_nacimiento': safe_iso(self.fecha_nacimiento),
            'domicilio': self.domicilio,
            'edad': self.edad,
            'sexo': self.sexo,
            'indigena': self.indigena,
            'migrante': self.migrante,
            'nivel_atencion': self.nivel_atencion,
            'consulta_enfermeria': self.consulta_enfermeria,
            'consultoria_otorgada': self.consultoria_otorgada,
            'prescripcion_medicamentos': self.prescripcion_medicamentos,
            'DG_plan_cuidados': self.DG_plan_cuidados,
            'DG_GRUPOS_EDAD': self.DG_GRUPOS_EDAD,
            'INSTITUCION_PROCEDENCIA': self.INSTITUCION_PROCEDENCIA,
            'CONSEJERIA_PF': self.CONSEJERIA_PF,
            'PF_GRUPOS_EDAD': self.PF_GRUPOS_EDAD,
            'PF_SUBSECUENTE': self.PF_SUBSECUENTE,
            'PF_METODO': self.PF_METODO,
            'VI_EMB_grupo_edad': self.VI_EMB_grupo_edad,
            'VI_EMB_TRIMESTRE_GESTACIONAL': self.VI_EMB_TRIMESTRE_GESTACIONAL,
            'VI_EMB_ACCIONES_IRREDUCTIBLES': self.VI_EMB_ACCIONES_IRREDUCTIBLES,
            'observaciones': self.observaciones,
            'DETECCION_TAMIZ': self.DETECCION_TAMIZ,
            'diagnostico_nutricional': self.diagnostico_nutricional,
            'SALUD_GINECO_DETECCION': self.SALUD_GINECO_DETECCION,
            'EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS': self.EDA_SOBRES_DE_HIDRATACION_ORAL_ENTREGADOS,
            'EDA_MADRES_CAPACITADAS_MANEJO': self.EDA_MADRES_CAPACITADAS_MANEJO,
            'IRA_MADRES_CAPACITADAS_MANEJO': self.IRA_MADRES_CAPACITADAS_MANEJO,
            'grupo_riesgo': self.grupo_riesgo,
            'DETECCION_ENFERMEDADES_CRONICAS': self.DETECCION_ENFERMEDADES_CRONICAS,
            'DIABETES_MELLITUS': self.DIABETES_MELLITUS,
            'DISLIPIDEMIA': self.DISLIPIDEMIA,
            'hipertension': self.hipertension,
            'REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES': self.REVISION_INTEGRAL_PIEL_MIEMBROS_INFERIORES,
            'DIABETICOS_INFORMADOS_CUIDADOS_PIES': self.DIABETICOS_INFORMADOS_CUIDADOS_PIES,
            'vacunacion': self.vacunacion,
            'PROMOCION_SALUD': self.PROMOCION_SALUD,
            'DERIVACION': self.DERIVACION,
            'ACTIVIDADES_ASISTENCIALES': self.ACTIVIDADES_ASISTENCIALES,
            'OBSERVACIONES_GENERALES': self.OBSERVACIONES_GENERALES,
        }

# Modelo Archivo
class Archivo(db.Model):
    __tablename__ = 'archivos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    nombre_formato = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(100), nullable=False)
    fecha_subida = db.Column(db.DateTime, server_default=db.func.now())
