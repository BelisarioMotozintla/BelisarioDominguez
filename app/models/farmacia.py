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
    principio_activo = Column(Text)
    stock_minimo = Column(Integer, default=10)  # valor crítico
    stock_maximo = Column(Integer, default=100) # nivel óptimo
    presentacion = Column(Text)
    via_administracion = Column(Text) #oral , inyectable
    concentracion = Column(Text)# gramaje 100 grm, 15 ml 
    unidad = Column(Text)

       # 🔹 Nuevos campos para los 3 catálogos
    es_kit_basico = Column(Boolean, default=False)  # Las 150 claves
    es_180_claves = Column(Boolean, default=False)  # El de 180 (incluye básicos)
    es_general = Column(Boolean, default=True)      # Todo lo de la unidad

    # CPM y nivel de movimiento

    cpm = Column(Float, default=0.0)  # Consumo Promedio Mensual
    nivel_movimiento = Column(
        Enum('Nulo', 'Bajo', 'Medio', 'Alto', name='nivel_movimiento_enum'),
        default='Nulo'
    )

    # Relaciones con otras tablas
    entrada_almacen = relationship('EntradaAlmacen', back_populates='medicamento')
    movimiento_almacen_farmacia = relationship('MovimientoAlmacenFarmacia', back_populates='medicamento')
    #salida_farmacia_paciente = relationship('SalidaFarmaciaPaciente', back_populates='medicamento')
    salidas_farmacia = relationship('SalidaFarmacia', back_populates='medicamento')
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
        from datetime import datetime, timedelta, timezone
        
        # 1. Usar timezone.utc (utcnow está en proceso de eliminación en Python 3.12+)
        fecha_limite = datetime.now(timezone.utc) - timedelta(days=30 * meses)
        
        # 2. Filtrar asegurando que la fecha no sea None y esté en el rango
        salidas_recientes = [
            s.cantidad for s in self.salida_farmacia_paciente 
            if s.fecha_salida and s.fecha_salida >= fecha_limite
        ]

        # 3. Calcular promedio
        if salidas_recientes:
            self.cpm = sum(salidas_recientes) / meses
        else:
            self.cpm = 0.0

        # 4. Actualizar nivel de movimiento con lógica simplificada
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
    lote = Column(String(50))
    fecha_vencimiento = Column(Date)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='movimiento_almacen_farmacia')
    usuario = relationship('Usuario', back_populates='movimientos_almacen_farmacia')


class SalidaFarmacia(db.Model):
    __tablename__ = 'SalidaFarmacia'
    
    id_salida = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'), nullable=False)
    cantidad = Column(Integer, nullable=False)
    lote = Column(String(50), nullable=False)
    fecha_vencimiento = Column(Date)
    fecha_salida = Column(TIMESTAMP, default=lambda: datetime.now(timezone.utc))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'), nullable=False)

    # El cambio principal: Tu abanico optimizado
    tipo_salida = Column(
        Enum('RECETA', 'COLECTIVO', 'BAJA_0C99', 'BAJA_CADUCIDAD', 'BAJA_EXTRAVIO', 'TRASLADO_UNIDAD', name='tipo_salida_enum'),
        nullable=False
    )
    
    # Campos condicionales (pueden ser Null/None si no es receta)
    id_receta = Column(Integer, ForeignKey('RecetaMedica.id_receta'), nullable=True) 
    entidad_destino = Column(String(100), nullable=True) # Ej: 'CEYE', 'URGENCIAS', 'HOSPITAL X'
    documento_soporte = Column(String(50), nullable=True) # Folio de vale, acta de extravío, u oficio
    
    receta = relationship('RecetaMedica', back_populates='salidas')
    medicamento = relationship('Medicamento', back_populates='salidas_farmacia')
    usuario = relationship('Usuario', back_populates='salidas_farmacia')

# Modelo SalidaFarmaciaPaciente esta por removerse por que se especializo
#class SalidaFarmaciaPaciente(db.Model):
#    __tablename__ = 'SalidaFarmaciaPaciente'
#    id_salida = Column(Integer, primary_key=True)
#    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
#    cantidad = Column(Integer, nullable=False)
#    fecha_salida = Column(TIMESTAMP, default=datetime.utcnow)
#    lote = Column(String(50))
#    fecha_vencimiento = Column(Date)
#    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))
    
    # CAMBIO: Usamos id_receta (Primary Key) en lugar de folio para la relación
#    id_receta = Column(Integer, ForeignKey('RecetaMedica.id_receta'), nullable=False)

#    medicamento = relationship('Medicamento', back_populates='salida_farmacia_paciente')
#    usuario = relationship('Usuario', back_populates='salida_farmacia_paciente')
    
    # SQLAlchemy entiende automáticamente que debe usar id_receta para el "join"
#    receta = relationship('RecetaMedica', back_populates='salidas')



# Modelo TransferenciaSaliente
class TransferenciaSaliente(db.Model):
    __tablename__ = 'TransferenciaSaliente'
    id_transferencia = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    fecha_transferencia = Column(TIMESTAMP)
    lote = Column(String(50))
    fecha_vencimiento = Column(Date)
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
    lote = Column(String(50))
    fecha_vencimiento = Column(Date)
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))

    medicamento = relationship('Medicamento', back_populates='transferencia_entrante')
    usuario = relationship('Usuario', back_populates='transferencias_entrantes')

# Modelo InventarioAlmacen
class InventarioAlmacen(db.Model):
    __tablename__ = 'InventarioAlmacen'
    id_inventario = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    lote = Column(String(50))
    fecha_vencimiento = Column(Date)
    medicamento = relationship('Medicamento', back_populates='inventario_almacen')

# Modelo InventarioFarmacia
class InventarioFarmacia(db.Model):
    __tablename__ = 'InventarioFarmacia'
    id_inventario = Column(Integer, primary_key=True)
    id_medicamento = Column(Integer, ForeignKey('Medicamento.id_medicamento'))
    cantidad = Column(Integer, nullable=False)
    lote = Column(String(50))
    fecha_vencimiento = Column(Date)

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
    
# Relación con diagnósticos asignados a pacientes diagnostico_paciente

    diagnosticos_paciente = db.relationship("DiagnosticoPaciente", back_populates="diagnostico_info")

class RecetaMedica(db.Model):
    __tablename__ = 'RecetaMedica'
    id_receta = Column(Integer, primary_key=True)
    
    id_asignacion = Column(Integer, ForeignKey('AsignacionReceta.id_asignacion'))
    id_paciente = Column(Integer, ForeignKey('Paciente.id_paciente'))
    id_usuario = Column(Integer, ForeignKey('Usuario.id_usuario'))  # médico que recetó
    
    folio = Column(String(50), nullable=False, unique=True) 
    fecha_emision = Column(TIMESTAMP, default=datetime.utcnow)
    tipo_surtimiento = Column(String(20), default="No surtida", nullable=False)
    #nota_id = db.Column(db.Integer, db.ForeignKey("nota_consulta_externa.id_nota"), unique=True, nullable=False)# esto es para que sea receta por nota
    nota_id = db.Column(db.Integer,db.ForeignKey("nota_consulta_externa.id_nota"),nullable=True,index=True)
    diagnostico_id = db.Column(db.Integer, db.ForeignKey('diagnostico.id_diagnostico'), nullable=False)
    
   

    # Relaciones
    asignacion = relationship('AsignacionReceta', back_populates='recetas')
    paciente = relationship('Paciente', back_populates='recetas')
    usuario = relationship('Usuario', back_populates='recetas')
    detalle = relationship('DetalleReceta', back_populates='receta')
    nota = db.relationship("NotaConsultaExterna", back_populates="receta", uselist=False)
    diagnostico = db.relationship('Diagnostico')

    # Relación a las salidas de farmacia
    salidas = relationship('SalidaFarmacia', back_populates='receta')
 
    # Property para calcular tipo de surtimiento dinámicamente
    @property
    def tipo_surtimiento_calculado(self):
        # Si la receta no tiene ninguna salida registrada en el historial
        if not self.salidas:
            return "No surtida"

        tiene_surtido_al_menos_uno = False
        tiene_negado_al_menos_uno = False

        # Analizamos renglón por renglón lo solicitado vs lo entregado en total
        for detalle_item in self.detalle:
            # Sumamos todas las salidas existentes para este medicamento específico en la receta
            total_surtido = sum(
                s.cantidad for s in self.salidas if s.id_medicamento == detalle_item.id_medicamento
            )
            
            if total_surtido > 0:
                tiene_surtido_al_menos_uno = True
                
            if total_surtido < detalle_item.cantidad:
                tiene_negado_al_menos_uno = True

        # Clasificación matemática exacta y limpia:
        if tiene_surtido_al_menos_uno and tiene_negado_al_menos_uno:
            return "Parcial"
        elif tiene_surtido_al_menos_uno and not tiene_negado_al_menos_uno:
            return "Completa"
        else:
            return "No surtida"
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
