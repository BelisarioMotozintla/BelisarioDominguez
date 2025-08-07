from datetime import date, datetime
from sqlalchemy import Column, Integer, Text, Date, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from app.utils.db import db
from app.models.personal import Usuario, Empleado
from app.models.archivo_clinico import Paciente

# Modelo Medicamentos
class Medicamento(db.Model):
    __tablename__ = 'Medicamento'
    id_medicamento = Column(Integer, primary_key=True)
    clave = Column(Text, unique=True, nullable=False)
    nombre_comercial = Column(Text, nullable=False)
    principio_activo = Column(Text)
    presentacion = Column(Text)
    via_administracion = Column(Text)
    concentracion = Column(Text)
    unidad = Column(Text)

    entrada_almacen = relationship('EntradaAlmacen', back_populates='medicamento')
    movimiento_almacen_farmacia = relationship('MovimientoAlmacenFarmacia', back_populates='medicamento')
    salida_farmacia_paciente = relationship('SalidaFarmaciaPaciente', back_populates='medicamento')
    transferencia_saliente = relationship('TransferenciaSaliente', back_populates='medicamento')
    transferencia_entrante = relationship('TransferenciaEntrante', back_populates='medicamento')
    inventario_almacen = relationship('InventarioAlmacen', back_populates='medicamento')
    inventario_farmacia = relationship('InventarioFarmacia', back_populates='medicamento')
    detalle_receta = relationship('DetalleReceta', back_populates='medicamento')
    bitacora_movimiento = relationship('BitacoraMovimiento', back_populates='medicamento')

# Modelo EntradaAlmacen
class EntradaAlmacen(db.Model):
    __tablename__ = 'EntradaAlmacen'
    id_entrada = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    lote = Column(Text)
    fecha_caducidad = Column(Date)
    fecha_entrada = Column(TIMESTAMP)
    proveedor = Column(Text)
    observaciones = Column(Text)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='entrada_almacen')
    usuario = relationship('Usuario', back_populates='entrada_almacenes')

# Modelo MovimientoAlmacenFarmacia
class MovimientoAlmacenFarmacia(db.Model):
    __tablename__ = 'MovimientoAlmacenFarmacia'
    id_movimiento = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    fecha_movimiento = Column(TIMESTAMP)
    observaciones = Column(Text)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='movimiento_almacen_farmacia')
    usuario = relationship('Usuario', back_populates='movimientos_almacen_farmacia')

# Modelo SalidaFarmaciaPaciente
class SalidaFarmaciaPaciente(db.Model):
    __tablename__ = 'SalidaFarmaciaPaciente'
    id_salida = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    fecha_salida = Column(TIMESTAMP)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='salida_farmacia_paciente')
    usuario = relationship('Usuario', back_populates='salida_farmacia_paciente')

# Modelo TransferenciaSaliente
class TransferenciaSaliente(db.Model):
    __tablename__ = 'TransferenciaSaliente'
    id_transferencia = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    fecha_transferencia = Column(TIMESTAMP)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='transferencia_saliente')
    usuario = relationship('Usuario', back_populates='transferencias_salientes')

# Modelo TransferenciaEntrante
class TransferenciaEntrante(db.Model):
    __tablename__ = 'TransferenciaEntrante'
    id_transferencia = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    fecha_transferencia = Column(TIMESTAMP)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='transferencia_entrante')
    usuario = relationship('Usuario', back_populates='transferencias_entrantes')

# Modelo InventarioAlmacen
class InventarioAlmacen(db.Model):
    __tablename__ = 'InventarioAlmacen'
    id_inventario = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)

    medicamento = relationship('Medicamento', back_populates='inventario_almacen')

# Modelo InventarioFarmacia
class InventarioFarmacia(db.Model):
    __tablename__ = 'InventarioFarmacia'
    id_inventario = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)

    medicamento = relationship('Medicamento', back_populates='inventario_farmacia')

# Modelo RangoFolios
class RangoFolios(db.Model):
    __tablename__ = 'RangoFolios'
    id_rango = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey('Empleado.id_empleado'))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))
    inicio = Column(Integer)
    fin = Column(Integer)

    empleado = relationship('Empleado', back_populates='rango_folios')
    usuario = relationship('Usuario', back_populates='rango_folios')

# Modelo RecetaMedica
class RecetaMedica(db.Model):
    __tablename__ = 'RecetaMedica'
    id_receta = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey('Empleado.id_empleado'))
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente'))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))
    fecha_emision = Column(TIMESTAMP)

    empleado = relationship('Empleado', back_populates='recetas_medicas')
    paciente = relationship(Paciente, back_populates='recetas')
    usuario = relationship('Usuario', back_populates='recetas')
    detalle = relationship('DetalleReceta', back_populates='receta')

# Modelo DetalleReceta
class DetalleReceta(db.Model):
    __tablename__ = 'DetalleReceta'
    id_detalle = Column(Integer, primary_key=True)
    id_receta = Column(Integer, ForeignKey('RecetaMedica.id_receta'))
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    dosis = Column(Text)
    indicaciones = Column(Text)

    receta = relationship('RecetaMedica', back_populates='detalle')
    medicamento = relationship('Medicamento', back_populates='detalle_receta')

# Modelo BitacoraAccion
class BitacoraAccion(db.Model):
    __tablename__ = 'BitacoraAccion'
    id_accion = Column(Integer, primary_key=True)
    accion = Column(Text)
    fecha_hora = Column(TIMESTAMP)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    usuario = relationship('Usuario', back_populates='bitacora_accion')

# Modelo BitacoraMovimiento
class BitacoraMovimiento(db.Model):
    __tablename__ = 'BitacoraMovimiento'
    id_bitacora = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))
    fecha_hora = Column(TIMESTAMP)
    movimiento = Column(Text)

    medicamento = relationship('Medicamento', back_populates='bitacora_movimiento')
    usuario = relationship('Usuario', back_populates='bitacora_movimiento')
