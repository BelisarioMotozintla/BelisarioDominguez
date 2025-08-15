# archivo_clinico.py

from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.utils.db import db
from app.models.personal import Usuario,Servicio
from datetime import date



# Modelo Unidad de Salud 009
class UnidadSalud(db.Model):
    __tablename__ = 'UnidadSalud'
    id_unidad = Column(Integer, primary_key=True)
    clues = Column(Text, unique=True, nullable=False)
    nombre = Column(Text, nullable=False)
    direccion = Column(Text)
    tipo_unidad = Column(Text)
    
    pacientes_unidad = relationship('PacienteUnidad', back_populates='unidad')  # ✅ STRING segura	
    empleados = relationship('Empleado', back_populates='unidad')

# Modelo Paciente 010
class Paciente(db.Model):
    __tablename__ = 'Paciente'
    id_paciente = Column(Integer, primary_key=True)
    nombre = Column(Text, nullable=False)
    curp = Column(Text, unique=True, nullable=False)
    fecha_nacimiento = Column(Date)
    sexo = Column(Text)
    direccion = Column(Text)
    es_cronico = Column(String(2), default='No')  # 'Sí' o 'No'
    tipo_cronicidad = Column(Text, nullable=True)  # 'Diabético', 'Hipertenso', 'Metabólico', etc.
    esta_embarazada = Column(String(2), default='No')

    __table_args__ = (
        CheckConstraint("sexo IN ('M', 'F', 'Otro')", name='chk_sexo'),
        CheckConstraint("es_cronico IN ('Sí', 'No')", name='chk_cronico'),
        CheckConstraint("esta_embarazada IN ('Sí', 'No')", name='chk_embarazo'),
        CheckConstraint("tipo_cronicidad IN ('Diabético', 'Hipertenso', 'Metabólico', 'Otro', '') OR tipo_cronicidad IS NULL", name='chk_tipo_cronicidad')
    )	
    paciente_unidad = relationship('PacienteUnidad', back_populates='paciente')
    archivo_clinico = relationship('ArchivoClinico', back_populates='paciente')
    recetas = relationship('RecetaMedica', back_populates='paciente')  # <- esto puede quedarse como string si viene de otro archivo
    solicitud_expediente = relationship('SolicitudExpediente', back_populates='paciente')
    
    @property
    def edad(self):
        if self.fecha_nacimiento:
            return (date.today() - self.fecha_nacimiento).days // 365
        return None
    

# Modelo PacienteUnidad 011
class PacienteUnidad(db.Model):
    __tablename__ = 'PacienteUnidad'
    id_paciente_unidad = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente'))
    id_unidad = Column(Integer, ForeignKey('UnidadSalud.id_unidad'))
    tipo_relacion = Column(Text, nullable=False)
    fecha_relacion = Column(Date)

    paciente = relationship(Paciente, back_populates='paciente_unidad')
    unidad = relationship(UnidadSalud, back_populates='pacientes_unidad')

# Modelo ArchivoClinico 012
class ArchivoClinico(db.Model):
    __tablename__ = 'ArchivoClinico'
    id_archivo = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente'))
    ubicacion_fisica = Column(Text)
    estado = Column(Text)  # disponible, prestado, extraviado
    tipo_archivo = Column(Text)
    fecha_creacion = Column(Date)
    numero_expediente = db.Column(db.String, unique=True)  # nuevo campo único editable
    __table_args__ = (
        CheckConstraint("estado IN ('disponible', 'prestado', 'extraviado')", name='chk_estado_archivo'),
    )

    paciente = relationship(Paciente, back_populates='archivo_clinico')
    solicitudes = relationship('SolicitudExpediente', back_populates='archivo')

# Modelo SolicitudExpediente 013
class SolicitudExpediente(db.Model):
    __tablename__ = 'SolicitudExpediente'
    id_solicitud = Column(Integer, primary_key=True)
    id_archivo = Column(Integer, ForeignKey('ArchivoClinico.id_archivo')) # el id del expediente
    id_usuario_solicita = Column(Integer, ForeignKey('Usuario.id_usuario'))# usuario que lo solicita 
    id_usuario_autoriza = Column(Integer, ForeignKey('Usuario.id_usuario')) # usuario que lo autoriza
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente')) # paciente
    fecha_solicitud = Column(TIMESTAMP)
    fecha_entrega = Column(TIMESTAMP)
    fecha_devolucion = Column(TIMESTAMP)
    estado_solicitud = Column(Text)  # pendiente, entregado, devuelto, cancelado
    id_servicio = Column(Integer, ForeignKey('Servicio.id_servicio'))

    __table_args__ = (
        CheckConstraint("estado_solicitud IN ('pendiente', 'entregado', 'devuelto', 'cancelado')", name='chk_estado_solicitud'),
    )

    archivo = relationship(ArchivoClinico, back_populates='solicitudes')
    usuario_solicita = relationship(Usuario, foreign_keys=[id_usuario_solicita], back_populates='solicitudes_solicita')
    usuario_autoriza = relationship(Usuario, foreign_keys=[id_usuario_autoriza], back_populates='solicitudes_autoriza')
    paciente = relationship(Paciente, back_populates='solicitud_expediente')
    servicio = relationship(Servicio, back_populates='solicitud_expediente')
