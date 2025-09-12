from datetime import date, datetime
from sqlalchemy import Column, Integer, Boolean, TIMESTAMP, Text, ForeignKey, CheckConstraint,Date,Float, Enum,String
from sqlalchemy.orm import relationship
from app.utils.db import db
from app.models.personal import Usuario, Empleado
from app.models.archivo_clinico import Paciente

# Modelo Medicamento con CPM y Nivel de Movimiento
class Medicamento(db.Model):
    __tablename__ = 'Medicamento'
    
    id_medicamento = Column(Integer, primary_key=True)
    clave = Column(Text, unique=True, nullable=False)
    nombre_comercial = Column(Text, nullable=False)
    stock_minimo = Column(Integer, default=10)  # valor crítico
    stock_maximo = Column(Integer, default=100) # nivel óptimo
    principio_activo = Column(Text)
    presentacion = Column(Text)
    via_administracion = Column(Text)
    concentracion = Column(Text)
    unidad = Column(Text)

    # CPM y nivel de movimiento
    cpm = Column(Float, default=0.0)  # Consumo Promedio Mensual
    nivel_movimiento = Column(
        Enum('Nulo', 'Bajo', 'Medio', 'Alto', name='nivel_movimiento_enum'),
        default='Nulo'
    )

    # Relaciones con otras tablas
    entrada_almacen = relationship('EntradaAlmacen', back_populates='medicamento')
    movimiento_almacen_farmacia = relationship('MovimientoAlmacenFarmacia', back_populates='medicamento')
    salida_farmacia_paciente = relationship('SalidaFarmaciaPaciente', back_populates='medicamento')
    transferencia_saliente = relationship('TransferenciaSaliente', back_populates='medicamento')
    transferencia_entrante = relationship('TransferenciaEntrante', back_populates='medicamento')
    inventario_almacen = relationship('InventarioAlmacen', back_populates='medicamento')
    inventario_farmacia = relationship('InventarioFarmacia', back_populates='medicamento')
    detalle_receta = relationship('DetalleReceta', back_populates='medicamento')
    bitacora_movimiento = relationship('BitacoraMovimiento', back_populates='medicamento')

    def calcular_cpm(self, meses=3):
        """
        Calcula el Consumo Promedio Mensual basado en salidas de los últimos 'meses' meses.
        """
        from datetime import datetime, timedelta
        fecha_limite = datetime.utcnow() - timedelta(days=30*meses)
        salidas_recientes = [s.cantidad for s in self.salida_farmacia_paciente if s.fecha_salida >= fecha_limite]
        if salidas_recientes:
            self.cpm = sum(salidas_recientes) / meses
        else:
            self.cpm = 0.0

        # Actualizar nivel de movimiento
        if self.cpm == 0:
            self.nivel_movimiento = 'Nulo'
        elif self.cpm <= 5:
            self.nivel_movimiento = 'Bajo'
        elif self.cpm <= 20:
            self.nivel_movimiento = 'Medio'
        else:
            self.nivel_movimiento = 'Alto'

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
    folio_receta = Column(Integer, ForeignKey('RecetaMedica.folio'), nullable=False)

    medicamento = relationship('Medicamento', back_populates='salida_farmacia_paciente')
    usuario = relationship('Usuario', back_populates='salida_farmacia_paciente')
    receta = relationship('RecetaMedica', back_populates='salidas')


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

class BloqueReceta(db.Model):
    __tablename__ = 'BloqueReceta'

    id_bloque = Column(Integer, primary_key=True)

    # Rango de folios físicos del talonario
    folio_inicio = Column(Integer, nullable=False)
    folio_fin = Column(Integer, nullable=False)

    # Quién creó/cargó este bloque (usuario administrativo)
    creado_por = Column(Integer, ForeignKey('Usuario.id_usuario'), nullable=False)
    fecha_creacion = Column(TIMESTAMP, default=datetime.utcnow)

    # Estado del bloque
    asignado = Column(Boolean, default=False, nullable=False)  # si ya fue asignado a algún médico
    activo = Column(Boolean, default=True, nullable=False)     # por si quieres deshabilitarlo

    # Relaciones
    creador = relationship('Usuario', foreign_keys=[creado_por])
    asignaciones = relationship(
        'AsignacionReceta',
        back_populates='bloque',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        CheckConstraint('folio_inicio <= folio_fin', name='ck_bloque_rango_valido'),
    )
	
class AsignacionReceta(db.Model):
    __tablename__ = 'AsignacionReceta'

    id_asignacion = Column(Integer, primary_key=True)
    id_bloque = Column(Integer, ForeignKey('BloqueReceta.id_bloque'))
    id_medico = Column(Integer, ForeignKey('Usuario.id_usuario'))
    id_asignador = Column(Integer, ForeignKey('Usuario.id_usuario'))
    fecha_asignacion = Column(TIMESTAMP, default=datetime.utcnow)
    folio_actual = Column(Integer, nullable=False)

    # Relaciones
    bloque = relationship('BloqueReceta', back_populates='asignaciones')

    medico = relationship(
        "Usuario",
        foreign_keys=[id_medico],
        back_populates="asignaciones_recetas"
    )

    asignador = relationship(
        "Usuario",
        foreign_keys=[id_asignador],
        back_populates="asignaciones_asignadas"
    )

    recetas = relationship('RecetaMedica', back_populates='asignacion')

    # Ya tienes
    def proximo_folio(self):
        """Devuelve el folio siguiente sin consumirlo"""
        if self.folio_actual > self.bloque.folio_fin:
            return None
        return self.folio_actual

    # 🔹 Nuevo método
    def siguiente_folio(self):
        """Devuelve el folio actual y lo incrementa para consumirlo"""
        if self.folio_actual > self.bloque.folio_fin:
            return None  # bloque agotado
        folio = self.folio_actual
        self.folio_actual += 1
        return folio

class Diagnostico(db.Model):
    __tablename__ = 'diagnostico'
    
    id_diagnostico = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), nullable=False, unique=True)  # Ej. "J45.9"
    descripcion = db.Column(db.String(255), nullable=False)

class RecetaMedica(db.Model):
    __tablename__ = 'RecetaMedica'
    id_receta = Column(Integer, primary_key=True)
    
    id_asignacion = Column(Integer, ForeignKey('AsignacionReceta.id_asignacion'))
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente'))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))  # médico que recetó
    
    folio = Column(Integer, nullable=False)
    fecha_emision = Column(TIMESTAMP, default=datetime.utcnow)
    tipo_surtimiento = Column(String(20), default="No surtida", nullable=False)
    nota_id = db.Column(db.Integer, db.ForeignKey("nota_consulta_externa.id_nota"), unique=True, nullable=False)
    diagnostico_id = db.Column(db.Integer, db.ForeignKey('diagnostico.id_diagnostico'), nullable=False)
   

    # Relaciones
    asignacion = relationship('AsignacionReceta', back_populates='recetas')
    paciente = relationship('Paciente', back_populates='recetas')
    usuario = relationship('Usuario', back_populates='recetas')
    detalle = relationship('DetalleReceta', back_populates='receta')
    nota = db.relationship("NotaConsultaExterna", back_populates="receta", uselist=False)
    diagnostico = db.relationship('Diagnostico')

    # Relación a las salidas de farmacia
    salidas = relationship('SalidaFarmaciaPaciente', back_populates='receta')
 
    # Property para calcular tipo de surtimiento dinámicamente
    @property
    def tipo_surtimiento_calculado(self):
        if not self.salidas:
            return "No surtida"

        completo, parcial = True, False

        for detalle in self.detalle:
            salida = next(
                (s for s in self.salidas if s.id_medicamento == detalle.id_medicamento),
                None
            )
            if not salida or salida.cantidad == 0:
                completo = False
            elif salida.cantidad < detalle.cantidad:
                completo = False
                parcial = True

        if completo:
            return "Completa"
        elif parcial:
            return "Parcial"
        return "No surtida"

class DetalleReceta(db.Model):
    __tablename__ = 'DetalleReceta'
    id_detalle = Column(Integer, primary_key=True)
    id_receta = Column(Integer, ForeignKey('RecetaMedica.id_receta'))
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))

    cantidad = Column(Integer, nullable=False)
    cantidad_surtida = Column(Integer, default=0, nullable=False)
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
