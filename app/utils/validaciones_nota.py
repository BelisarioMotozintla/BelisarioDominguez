from datetime import datetime, date
from decimal import Decimal

# Funciones auxiliares para convertir y normalizar datos
def get_str(datos, key):
    return datos.get(key, '').strip().upper()

def get_date(datos, key, fmt="%Y-%m-%d"):
    val = datos.get(key, "")
    if val is None or val == "":
        return None
    
    # Si ya es date o datetime, regresamos como date
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    
    # Si es string, intentamos parsear
    if isinstance(val, str):
        val = val.strip()
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            return None
    
    return None
def get_time(datos, key):
    val = datos.get(key, '').strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, '%H:%M').time()
    except:
        return None

def get_int(datos, key):
    val = datos.get(key, "")
    if val is None:
        return None
    
    # Si ya es numérico
    if isinstance(val, (int, float, Decimal)):
        return int(val)
    
    # Si es cadena
    if isinstance(val, str):
        val = val.strip()
        try:
            return int(val) if val else None
        except ValueError:
            return None
    
    return None


def get_float(datos, key):
    val = datos.get(key, "")
    if val is None:
        return None
    
    # Si ya es numérico
    if isinstance(val, (int, float, Decimal)):
        return float(val)
    
    # Si es cadena
    if isinstance(val, str):
        val = val.strip()
        try:
            return float(val) if val else None
        except ValueError:
            return None
    
    return None
# Validación de todos los campos de nota médica
def campos_validos_nota_medica(datos):
    errores = []

    # Signos vitales
    peso = get_float(datos, 'peso')
    talla = get_float(datos, 'talla')
    if peso < 0:
        errores.append('Peso no puede ser negativo')
    if talla < 0:
        errores.append('Talla no puede ser negativa')

    ta = get_str(datos, 'ta') or "0/0"

    fc = get_int(datos, 'fc')
    fr = get_int(datos, 'fr')
    temp = get_float(datos, 'temp')
    spo2 = get_int(datos, 'spo2')
    glicemia = get_int(datos, 'glicemia')

    if fc < 0:
        errores.append('FC no puede ser negativa')
    if fr < 0:
        errores.append('FR no puede ser negativa')
    if temp < 0:
        errores.append('Temperatura no puede ser negativa')
    if spo2 < 0:
        errores.append('SpO2 no puede ser negativa')
    if glicemia < 0:
        errores.append('Glicemia no puede ser negativa')

    # Fecha
    fecha = get_date(datos, 'fecha')
    if not fecha:
        errores.append('Fecha inválida o vacía')

    # Campos de texto
    campos_texto = ['antecedentes', 'exploracion_fisica', 'diagnostico',
                    'plan', 'pronostico', 'laboratorio']
    textos = {c: get_str(datos, c) for c in campos_texto}

    return errores, {
        'peso': peso,
        'talla': talla,
        'ta': ta,
        'fc': fc,
        'fr': fr,
        'temp': temp,
        'spo2': spo2,
        'glicemia': glicemia,
        'fecha': fecha,
        **textos
    }

def calcular_imc(peso, talla):
    """Calcula IMC en kg/m2"""
    try:
        return round(peso / (talla**2), 2) if peso > 0 and talla > 0 else 0
    except:
        return 0