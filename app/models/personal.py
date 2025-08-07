# personal.py

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date,Time
from sqlalchemy.orm import relationship
from app.utils.db import db
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Modelo Puesto 001
class Puesto(db.Model):
    __tablename__ = 'Puesto'
    id_puesto = Column(Integer, primary_key=True)
    codigo_puesto = Column(String(20))
    descripcion = Column(String(100))
    clave_codigo_funcional = Column(String(50))

    empleados = relationship('Empleado', back_populates='puesto')

# Modelo Turno 002
class Turno(db.Model):
    __tablename__ = 'Turno'
    id_turno = Column(Integer, primary_key=True)
    nombre_turno = Column(String(50))
    horario_entrada = Column(Time, nullable=False)
    horario_salida = Column(Time, nullable=False)
    
    horas_laborales = Column(Integer, nullable=False)
    
    dias_laborales = Column(String(100), nullable=False)   # Ejemplo: "Lunes a Viernes"
    dias_descanso = Column(String(100), nullable=True)      # Ejemplo: "Sábado, Domingo"

    empleados = relationship('Empleado', back_populates='turno')

    def __repr__(self):
        return f"<Turno {self.nombre_turno} {self.horario_entrada}-{self.horario_salida}>"

# Modelo Adscripción 003
class Adscripcion(db.Model):
    __tablename__ = 'Adscripcion'
    id_adscripcion = Column(Integer, primary_key=True)
    clues = Column(String(12), unique=True, nullable=False)
    nombre_adscripcion = Column(String(100))
    direccion = Column(String(150))

    empleados = relationship('Empleado', back_populates='adscripcion')

# Modelo Servicio 004
class Servicio(db.Model):
    __tablename__ = 'Servicio'
    id_servicio = Column(Integer, primary_key=True)
    nombre_servicio = Column(String(100))
    area = Column(String(100))

    empleados = relationship('Empleado', back_populates='servicio')
    solicitud_expediente = relationship('SolicitudExpediente', back_populates='servicio')

# Modelo Empleado 005
class Empleado(db.Model):
    __tablename__ = 'Empleado'
    id_empleado = Column(Integer, primary_key=True)
    tipo_trabajador = Column(String(50))  # <--- ¿Está esta línea?
    curp = Column(String(18), unique=True, nullable=False)
    rfc = Column(String(13), unique=True)
    no_biometrico = Column(String(10))
    nombre = Column(String(100))
    apellido_paterno = Column(String(100))
    apellido_materno = Column(String(100))
    titulo = Column(String(100))
    cedula = Column(String(20))
    fecha_ingreso = db.Column(Date)
    horario = Column(String(50))
    dias_laborables = Column(String(50))
    horas_laborales = Column(Integer)
    email = Column(String(120))
    telefono = Column(String(20))
    direccion = Column(Text)

    id_puesto = Column(Integer, ForeignKey('Puesto.id_puesto'))
    id_turno = Column(Integer, ForeignKey('Turno.id_turno'))
    id_adscripcion = Column(Integer, ForeignKey('Adscripcion.id_adscripcion'))
    id_servicio = Column(Integer, ForeignKey('Servicio.id_servicio'))

    # Relaciones
    puesto = relationship('Puesto', back_populates='empleados')
    turno = relationship('Turno', back_populates='empleados')
    adscripcion = relationship('Adscripcion', back_populates='empleados')
    servicio = relationship('Servicio', back_populates='empleados')
    estudios = relationship('Estudios', back_populates='empleado')
    usuarios = relationship('Usuario', back_populates='empleado')
    rango_folios = relationship('RangoFolios', back_populates='empleado')
    recetas_medicas = relationship('RecetaMedica', back_populates='empleado')

# Modelo Estudios 006
class Estudios(db.Model):
    __tablename__ = 'Estudios'
    id_estudios = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey('Empleado.id_empleado'))
    nivel = Column(String(50))

    empleado = relationship('Empleado', back_populates='estudios')

# Modelo Roles 007
class Roles(db.Model):
    __tablename__ = 'Roles'
    id_rol = Column(Integer, primary_key=True)
    nombre_rol = Column(Text)
    descripcion = Column(Text)

    usuarios = relationship('Usuario', back_populates='rol')

# Modelo Usuario 008
class Usuario(db.Model):
    __tablename__ = 'Usuario'
    id_usuario = Column(Integer, primary_key=True)
    usuario = Column(Text, unique=True, nullable=False)
    contrasena_hash = Column(Text, nullable=False)
    rol_id = Column(Integer, ForeignKey('Roles.id_rol'))
    id_empleado = Column(Integer, ForeignKey('Empleado.id_empleado'))

    rol = relationship('Roles', back_populates='usuarios')
    empleado = relationship('Empleado', back_populates='usuarios')

    entrada_almacenes = relationship('EntradaAlmacen', back_populates='usuario')
    movimientos_almacen_farmacia = relationship('MovimientoAlmacenFarmacia', back_populates='usuario')
    salida_farmacia_paciente = relationship('SalidaFarmaciaPaciente', back_populates='usuario')
    transferencias_salientes = relationship('TransferenciaSaliente', back_populates='usuario')
    transferencias_entrantes = relationship('TransferenciaEntrante', back_populates='usuario')
    recetas = relationship('RecetaMedica', back_populates='usuario')
    rango_folios = relationship('RangoFolios', back_populates='usuario')
    bitacora_accion = relationship('BitacoraAccion', back_populates='usuario')
    bitacora_movimiento = relationship('BitacoraMovimiento', back_populates='usuario')

    solicitudes_solicita = relationship(
        'SolicitudExpediente',
        foreign_keys='SolicitudExpediente.id_usuario_solicita',
        back_populates='usuario_solicita'
    )
    solicitudes_autoriza = relationship(
        'SolicitudExpediente',
        foreign_keys='SolicitudExpediente.id_usuario_autoriza',
        back_populates='usuario_autoriza'
    )

    def set_password(self, password):
        self.contrasena_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.contrasena_hash, password)

    def __repr__(self):
        return f'<Usuario {self.usuario}>'
