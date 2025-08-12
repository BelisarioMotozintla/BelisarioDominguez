ffrom sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.utils.db import db


class NotaConsultaExterna(db.Model):
    __tablename__ = 'nota_consulta_externa'

    id_nota = db.Column(db.Integer, primary_key=True)
    id_paciente = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    id_expediente = db.Column(db.Integer, db.ForeignKey('expediente_clinico.id'), nullable=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=True)

    peso = db.Column(db.Numeric(5,2), nullable=True)
    talla = db.Column(db.Numeric(5,2), nullable=True)
    ta = db.Column(db.String(20), nullable=True)   # tensión arterial
    fc = db.Column(db.Integer, nullable=True)
    fr = db.Column(db.Integer, nullable=True)
    temp = db.Column(db.Numeric(4,1), nullable=True)
    cc = db.Column(db.String(100), nullable=True)
    spo2 = db.Column(db.Integer, nullable=True)
    glicemia = db.Column(db.Integer, nullable=True)
    imc = db.Column(db.Numeric(5,2), nullable=True)

    antecedentes = db.Column(db.Text, nullable=True)
    exploracion_fisica = db.Column(db.Text, nullable=True)
    diagnostico = db.Column(db.Text, nullable=True)
    plan = db.Column(db.Text, nullable=True)
    pronostico = db.Column(db.Text, nullable=True)
    laboratorio = db.Column(db.Text, nullable=True)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones (opcional, para acceder a datos relacionados)
    paciente = db.relationship('Paciente', backref=db.backref('notas_consulta', lazy='dynamic'))
    expediente = db.relationship('ExpedienteClinico', backref=db.backref('notas_consulta', lazy='dynamic'))
    usuario = db.relationship('Usuario', backref=db.backref('notas_consulta', lazy='dynamic'))
