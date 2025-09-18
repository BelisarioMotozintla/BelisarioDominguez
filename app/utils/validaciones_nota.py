from datetime import datetime, date
from decimal import Decimal

# Funciones auxiliares para convertir y normalizar datos
def get_str(datos, key):
    return datos.get(key, '').strip().upper() if datos.get(key) else ''

def get_date(datos, key, fmt="%Y-%m-%d"):
    val = datos.get(key, "")
    if val is None or val == "":
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    if isinstance(val, str):
        val = val.strip()
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            return None
    return None

def get_time(datos, key):
    val = datos.get(key, '')
    if not val:
        return None
    if isinstance(val, datetime):
        return val.time()
    try:
        return datetime.strptime(val.strip(), '%H:%M').time()
    except:
        return None

def get_int(datos, key):
    val = datos.get(key, "")
    if val is None:
        return None
    if isinstance(val, (int, float, Decimal)):
        return int(val)
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
    if isinstance(val, (int, float, Decimal)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        try:
            return float(val) if val else None
        except ValueError:
            return None
    return None

def campos_validos_nota_medica(datos):
    errores = []

    # Signos vitales
    peso = get_float(datos, 'peso')
    talla = get_float(datos, 'talla')
    cc = get_float(datos, 'cc')
    ta = get_str(datos, 'ta') or "0/0"
    fc = get_int(datos, 'fc')
    fr = get_int(datos, 'fr')
    temp = get_float(datos, 'temp')
    spo2 = get_int(datos, 'spo2')
    glicemia = get_int(datos, 'glicemia')

    # Validaciones
    if peso is not None and peso < 0:
        errores.append('Peso no puede ser negativo')
    if talla is not None and talla < 0:
        errores.append('Talla no puede ser negativa')
    if cc is not None and cc < 0:
        errores.append('CC no puede ser negativa')
    if fc is not None and fc < 0:
        errores.append('FC no puede ser negativa')
    if fr is not None and fr < 0:
        errores.append('FR no puede ser negativa')
    if temp is not None and temp < 0:
        errores.append('Temperatura no puede ser negativa')
    if spo2 is not None and spo2 < 0:
        errores.append('SpO2 no puede ser negativa')
    if glicemia is not None and glicemia < 0:
        errores.append('Glicemia no puede ser negativa')

    # Fecha
    fecha = get_date(datos, 'fecha')
    if not fecha:
        errores.append('Fecha inválida o vacía')

    # Campos de texto (SOAP)
    campos_texto = ['antecedentes', 'exploracion_fisica',
                    'diagnostico', 'plan', 'pronostico', 'laboratorio']
    textos = {c: get_str(datos, c) for c in campos_texto}

    return errores, {
        'peso': peso,
        'talla': talla,
        'cc': cc,
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
