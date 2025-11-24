from sqlalchemy import Column, Integer, String, Text, Date, Time, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.db import db
from datetime import datetime

# --------------------- MODELO CONSULTA ---------------------
class Consulta(db.Model):
    __tablename__ = 'consulta'
    id_consulta = db.Column(db.Integer, primary_key=True)
    
    # Relación con paciente
    id_paciente = db.Column(db.Integer, db.ForeignKey('Paciente.id_paciente'), nullable=False)
    paciente = db.relationship('Paciente', backref=db.backref('consultas', lazy='dynamic'))
    
    # Usuario que abre la consulta (puede ser médico o pasante)
    id_usuario = db.Column(db.Integer, db.ForeignKey('Usuario.id_usuario'), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('consultas', lazy='dynamic'), foreign_keys=[id_usuario])

    fecha = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    estado = db.Column(db.String(20), default='ABIERTA')

    # Notas de la consulta
    notas = db.relationship('NotaConsultaExterna', back_populates='consulta', cascade="all, delete-orphan")


# --------------------- MODELO NOTA CONSULTA ---------------------
class NotaConsultaExterna(db.Model):
    __tablename__ = 'nota_consulta_externa'
    id_nota = db.Column(db.Integer, primary_key=True)
    
    # Relación con la consulta
    id_consulta = db.Column(db.Integer, db.ForeignKey('consulta.id_consulta'), nullable=False)
    consulta = db.relationship('Consulta', back_populates='notas')
    
    # Servicio de la nota
    id_servicio = db.Column(db.Integer, db.ForeignKey('Servicio.id_servicio'), nullable=False)
    servicio = db.relationship('Servicio', backref=db.backref('notas', lazy='dynamic'))

    # Usuario responsable de la nota (nutrición, psicología o médico)
    usuario_id = db.Column(db.Integer, db.ForeignKey('Usuario.id_usuario'), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('notas', lazy='dynamic'), foreign_keys=[usuario_id])

    # Fecha y hora
    fecha = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Signos vitales
    peso = db.Column(db.Numeric(5,2), nullable=True)
    talla = db.Column(db.Numeric(5,2), nullable=True)
    imc = db.Column(db.Numeric(5,2), nullable=True)
    ta = db.Column(db.String(20), nullable=True)
    fc = db.Column(db.Integer, nullable=True)
    fr = db.Column(db.Integer, nullable=True)
    temp = db.Column(db.Numeric(4,1), nullable=True)
    cc = db.Column(db.Numeric(5,2), nullable=True)
    spo2 = db.Column(db.Integer, nullable=True)
    glicemia = db.Column(db.Integer, nullable=True)

    # SOAP
    #presentacion = db.Column(db.Text, nullable=True) se elimina presentacion por que son los datos del paciente nombre, edad, curp
    antecedentes = db.Column(db.Text, nullable=True)
    exploracion_fisica = db.Column(db.Text, nullable=True)
    diagnostico = db.Column(db.Text, nullable=True)
    plan = db.Column(db.Text, nullable=True)
    pronostico = db.Column(db.Text, nullable=True)
    laboratorio = db.Column(db.Text, nullable=True)
    receta = db.relationship("RecetaMedica", back_populates="nota", uselist=False)

#==================================================================================folio============================
class FolioCertificado(db.Model):
    __tablename__ = "folio_certificado"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.Integer, unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    # Métodos utilitarios
    @staticmethod
    def generar_folio():
        """Devuelve el siguiente folio consecutivo"""
        ultimo = db.session.query(FolioCertificado).order_by(FolioCertificado.folio.desc()).first()
        if ultimo:
            return ultimo.folio + 1
        return 1
#========================================================cronicos====================================================
class DiagnosticoPaciente(db.Model):
    __tablename__ = 'diagnostico_paciente'

    id = db.Column(db.Integer, primary_key=True)

    id_paciente = db.Column(db.Integer, db.ForeignKey('Paciente.id_paciente'), nullable=False)
    id_diagnostico = db.Column(db.Integer, db.ForeignKey('diagnostico.id_diagnostico'), nullable=False)
    id_control = db.Column(
    db.Integer,
    db.ForeignKey('control_clinico.id_control', ondelete="CASCADE"),
    nullable=False
)
    fecha = db.Column(db.Date)

    # Relaciones limpias
    paciente = db.relationship("Paciente", back_populates="diagnosticos")
    diagnostico_info = db.relationship("Diagnostico", back_populates="diagnosticos_paciente")

 
    tratamientos = db.relationship(
        "TratamientoFarmacologico",
        back_populates="diagnostico",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True
    )
class TratamientoFarmacologico(db.Model):
    __tablename__ = 'tratamiento_farmacologico'

    id_tratamiento = db.Column(db.Integer, primary_key=True)
    id_dx = db.Column(
        db.Integer, 
        db.ForeignKey('diagnostico_paciente.id', ondelete='CASCADE'),
        nullable=False
    )

    diagnostico = db.relationship("DiagnosticoPaciente", back_populates="tratamientos")

    medicamentos = db.relationship(
        "MedicamentoTratamiento",
        back_populates="tratamiento",
        cascade="all, delete-orphan",
        lazy=True
    )


class MedicamentoTratamiento(db.Model):
    __tablename__ = 'medicamento_tratamiento'

    id = db.Column(db.Integer, primary_key=True)

    id_tratamiento = db.Column(
        db.Integer, 
        db.ForeignKey('tratamiento_farmacologico.id_tratamiento', ondelete='CASCADE')
    )

    id_medicamento = db.Column(
        db.Integer, 
        db.ForeignKey('Medicamento.id_medicamento'), 
        nullable=False
    )

    dosis = db.Column(db.String(100))
    frecuencia = db.Column(db.String(100))
    fecha_inicio = db.Column(db.Date)
    fecha_fin = db.Column(db.Date)

    tratamiento = db.relationship("TratamientoFarmacologico", back_populates="medicamentos")
    medicamento = db.relationship("Medicamento")


class ControlClinico(db.Model):
    __tablename__ = 'control_clinico'

    id_control = db.Column(db.Integer, primary_key=True)
    id_paciente = db.Column(db.Integer, db.ForeignKey('Paciente.id_paciente'), nullable=False)

    fecha_control = db.Column(db.Date)

    paciente = db.relationship("Paciente", back_populates="controles")

    laboratorio = db.relationship(
        "Laboratorio",
        uselist=False,
        back_populates="control",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    signos_vitales = db.relationship(
        "SignosVitales",
        uselist=False,
        back_populates="control",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    pie_diabetico = db.relationship(
        "PieDiabetico",
        uselist=False,
        back_populates="control",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    diagnosticos = db.relationship(
        "DiagnosticoPaciente",
        backref="control",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy=True
    )

class Laboratorio(db.Model):
    __tablename__ = 'laboratorio'

    id_laboratorio = db.Column(db.Integer, primary_key=True)
    id_control = db.Column(db.Integer, db.ForeignKey('control_clinico.id_control', ondelete="CASCADE"), nullable=False )
    glucosa = db.Column(db.Float)
    colesterol_total = db.Column(db.Float)
    hdl = db.Column(db.Float)
    ldl = db.Column(db.Float)
    trigliceridos = db.Column(db.Float)
    hba1c = db.Column(db.Float)
    microalbumina = db.Column(db.Float)

    control = db.relationship("ControlClinico", back_populates="laboratorio")



class SignosVitales(db.Model):
    __tablename__ = 'signos_vitales'

    id_sv = db.Column(db.Integer, primary_key=True)
    id_control = db.Column(
        db.Integer,
        db.ForeignKey('control_clinico.id_control', ondelete="CASCADE"),
        nullable=False
    )

    talla = db.Column(db.Float)
    peso = db.Column(db.Float)
    imc = db.Column(db.Float)
    cintura = db.Column(db.Float)

    presion_sistolica = db.Column(db.Integer)
    presion_diastolica = db.Column(db.Integer)

    control = db.relationship("ControlClinico", back_populates="signos_vitales")



class PieDiabetico(db.Model):
    __tablename__ = 'pie_diabetico'

    id_pie = db.Column(db.Integer, primary_key=True)
    id_control = db.Column(
        db.Integer,
        db.ForeignKey('control_clinico.id_control', ondelete="CASCADE"),
        nullable=False
    )

    clasificacion_pie = db.Column(db.String(10))
    observaciones = db.Column(db.Text)

    control = db.relationship("ControlClinico", back_populates="pie_diabetico")
