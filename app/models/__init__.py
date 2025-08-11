#from .personal import Puesto, Servicio,Turno, Empleado, Estudios,Roles, Usuario
#from .archivo_clinico import UnidadSalud, Paciente, PacienteUnidad, ArchivoClinico, SolicitudExpediente
#from .enfermeria import RegistroAdultoMayor, Archivo
#from .farmacia import Medicamento, EntradaAlmacen, MovimientoAlmacenFarmacia, SalidaFarmaciaPaciente, TransferenciaSaliente, TransferenciaEntrante, InventarioAlmacen, #InventarioFarmacia, RangoFolios, RecetaMedica, DetalleReceta, BitacoraAccion, BitacoraMovimiento
#from . import personal
#from . import archivo_clinico
#from . import enfermeria
#from . import farmacia

# Opción: puedes definir una lista __all__ para mayor claridad
#__all__ = [
#    "personal",
#    "archivo_clinico",
#    "enfermeria",
#    "farmacia"
#]
# app/models/__init__.py

from .archivo_clinico import UnidadSalud, Paciente, PacienteUnidad, ArchivoClinico, SolicitudExpediente
from .personal import Usuario, Roles, Empleado, Turno, Puesto, Servicio, Estudios
from .farmacia import Medicamento, EntradaAlmacen, MovimientoAlmacenFarmacia, SalidaFarmaciaPaciente, TransferenciaSaliente, TransferenciaEntrante, InventarioAlmacen, InventarioFarmacia, RangoFolios, RecetaMedica, DetalleReceta, BitacoraAccion, BitacoraMovimiento
from .enfermeria import RegistroAdultoMayor, Archivo

__all__ = [
    "UnidadSalud", "Paciente", "PacienteUnidad", "ArchivoClinico", "SolicitudExpediente",
    "Usuario", "Roles", "Empleado", "Turno", "Puesto", "Servicio", "Estudios",
    "Medicamento", "EntradaAlmacen", "MovimientoAlmacenFarmacia", "SalidaFarmaciaPaciente",
    "TransferenciaSaliente", "TransferenciaEntrante", "InventarioAlmacen", "InventarioFarmacia",
    "RangoFolios", "RecetaMedica", "DetalleReceta", "BitacoraAccion", "BitacoraMovimiento",
    "RegistroAdultoMayor", "Archivo"
]
