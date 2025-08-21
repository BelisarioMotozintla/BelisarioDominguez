from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.utils.db import db
from datetime import datetime

class Consulta(db.Model):
    __tablename__ = 'consulta'

    id_consulta = db.Column(db.Integer, primary_key=True)
    id_paciente = db.Column(db.Integer, db.ForeignKey('Paciente.id_paciente'), nullable=False)
    id_expediente = db.Column(db.Integer, db.ForeignKey('ArchivoClinico.id_archivo'), nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('Usuario.id_usuario'), nullable=False)  # Médico tratante
    id_servicio = db.Column(db.Integer, db.ForeignKey('Servicio.id_servicio'), nullable=False)

    fecha = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    hora = db.Column(db.Time, nullable=True)
    estado = db.Column(db.String(20), default='ABIERTA')

    # Relaciones
    paciente = db.relationship('Paciente', backref=db.backref('consultas', lazy='dynamic'))
    expediente = db.relationship('ArchivoClinico', backref=db.backref('consultas', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('consultas', lazy='dynamic'))
    servicio = db.relationship('Servicio', backref=db.backref('consultas', lazy='dynamic'))

    notas = db.relationship('NotaConsultaExterna', back_populates='consulta', cascade="all, delete-orphan")



class NotaConsultaExterna(db.Model):
    __tablename__ = 'nota_consulta_externa'

    id_nota = db.Column(db.Integer, primary_key=True)
    id_consulta = db.Column(db.Integer, db.ForeignKey('consulta.id_consulta'), nullable=False)

    fecha = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    hora = db.Column(db.Time, nullable=True)

    

    # Signos vitales
    peso = db.Column(db.Numeric(5,2), nullable=True)
    talla = db.Column(db.Numeric(5,2), nullable=True)
    ta = db.Column(db.String(20), nullable=True)
    fc = db.Column(db.Integer, nullable=True)
    fr = db.Column(db.Integer, nullable=True)
    temp = db.Column(db.Numeric(4,1), nullable=True)
    spo2 = db.Column(db.Integer, nullable=True)
    glicemia = db.Column(db.Integer, nullable=True)
    imc = db.Column(db.Numeric(5,2), nullable=True)

    # SOAP
    # Subjetivo
    presentacion = db.Column(db.Text, nullable=True)
    antecedentes = db.Column(db.Text, nullable=True)
    exploracion_fisica = db.Column(db.Text, nullable=True)
    diagnostico = db.Column(db.Text, nullable=True)
    plan = db.Column(db.Text, nullable=True)
    pronostico = db.Column(db.Text, nullable=True)
    laboratorio = db.Column(db.Text, nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relación
    consulta = db.relationship('Consulta', back_populates='notas')
