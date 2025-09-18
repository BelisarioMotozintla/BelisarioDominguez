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