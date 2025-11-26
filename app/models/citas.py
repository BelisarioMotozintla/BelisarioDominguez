from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, CheckConstraint,Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.utils.db import db
from datetime import date
from sqlalchemy import and_, or_
from datetime import datetime, timezone


class Consultorio(db.Model):
    __tablename__ = "Consultorio"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(250), nullable=True)

    citas = db.relationship("Cita", back_populates="consultorio")
    
class Cita(db.Model):
    __tablename__ = "Cita"

    id = db.Column(db.Integer, primary_key=True)

    uuid_publico = db.Column(
        db.String(36),
        unique=True,
        default=lambda: str(uuid.uuid4())
    )

    # Relación con Paciente
    paciente_id = db.Column(
        db.Integer,
        db.ForeignKey("Paciente.id_paciente"),
        nullable=True
    )
    paciente = db.relationship("Paciente", back_populates="citas")

    # Datos del solicitante (si no existe paciente registrado)
    solicitante_nombre = db.Column(db.String(250))
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))

    # Consultorio
    consultorio_id = db.Column(
        db.Integer,
        db.ForeignKey("Consultorio.id"),
        nullable=True
    )
    consultorio = db.relationship("Consultorio", back_populates="citas")

    # Fecha de la cita
    fecha_hora = db.Column(db.DateTime, nullable=False)
    duracion_min = db.Column(db.Integer, default=20)

    # Estado de flujo de la cita
    estado = db.Column(
        db.String(30),
        default='pendiente' 
        # valores posibles:
        # pendiente, confirmada, atendida,
        # cancelada, reprogramada, no_show
    )

    # Usuarios (crea/atiende)
    creado_por = db.Column(db.Integer, db.ForeignKey("Usuario.id_usuario"))
    atendido_por = db.Column(db.Integer, db.ForeignKey("Usuario.id_usuario"))

    # Extra
    motivo = db.Column(db.String(500))
    observaciones = db.Column(db.String(1000))

    # Timestamps seguros para Python 3.12+
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Evitar doble reserva por consultorio + hora exacta
    __table_args__ = (
        UniqueConstraint('consultorio_id', 'fecha_hora', name='uq_consultorio_fecha'),
    )
class Disponibilidad(db.Model):
    __tablename__ = "Disponibilidad"
    id = db.Column(db.Integer, primary_key=True)

    consultorio_id = db.Column(
        db.Integer,
        db.ForeignKey("Consultorio.id")
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("Usuario.id_usuario")
    )

    dia_semana = db.Column(db.Integer, nullable=False) # 0=lunes ... 6=domingo
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)

class Notificacion(db.Model):
    __tablename__ = "Notificacion"
    id = db.Column(db.Integer, primary_key=True)

    cita_id = db.Column(db.Integer, db.ForeignKey("Cita.id"))
    tipo = db.Column(db.String(50))  # email, sms, recordatorio
    enviado = db.Column(db.Boolean, default=False)
    enviado_en = db.Column(db.DateTime)


def hay_solapamiento(session, consultorio_id, start_dt, end_dt, exclude_cita_id=None):
    q = session.query(Cita).filter(Cita.consultorio_id == consultorio_id)
    if exclude_cita_id:
        q = q.filter(Cita.id != exclude_cita_id)
    # condición de solapamiento
    q = q.filter(
        or_(
            and_(Cita.fecha_hora <= start_dt, (Cita.fecha_hora + func.make_interval(mins=Cita.duracion_min)) > start_dt),
            and_(Cita.fecha_hora < end_dt, (Cita.fecha_hora + func.make_interval(mins=Cita.duracion_min)) >= end_dt),
            and_(Cita.fecha_hora >= start_dt, (Cita.fecha_hora + func.make_interval(mins=Cita.duracion_min)) <= end_dt)
        )
    )
    return session.query(q.exists()).scalar()