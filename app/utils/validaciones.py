# utils/validaciones.py
from datetime import datetime

def get_str(form, key):
    return form.get(key, '').strip().upper()

def get_date(form, key):
    val = form.get(key, '').strip()
    if not val:
        return None
    try:
        return datetime.strptime(val, '%Y-%m-%d').date()
    except:
        return None

def get_int(form, key):
    val = form.get(key, '').strip()
    try:
        return int(val)
    except:
        return None

def get_float(form, key):
    val = form.get(key, '').strip()
    try:
        return float(val)
    except:
        return None

def get_list_as_str(form, key):
    vals = form.getlist(key)
    return ','.join([v.upper() for v in vals]) if vals else ''


def campos_validos(form):
    # Campos que no pueden estar vacíos
    campos_obligatorios = [
        'unidad_salud', 'fecha', 'hora_inicio', 'hora_termino',
        'edad', 'nombre_jefe_fam', 'paciente', 'domicilio'
    ]

    for campo in campos_obligatorios:
        valor = form.get(campo, '').strip()
        if valor == '':
            return False, campo

    # Edad
    try:
        edad = int(form.get('edad', '').strip())
        if edad < 0:
            return False, 'edad (valor no válido)'
    except ValueError:
        return False, 'edad (no numérico)'

    # Fecha
    try:
        fecha = datetime.strptime(form.get('fecha', '').strip(), '%Y-%m-%d')
        if fecha > datetime.now():
            return False, 'fecha (futura)'
    except ValueError:
        return False, 'fecha (formato inválido)'

    # Hora inicio / término
    try:
        inicio = datetime.strptime(form.get('hora_inicio', '').strip(), '%H:%M')
        fin = datetime.strptime(form.get('hora_termino', '').strip(), '%H:%M')
        if inicio >= fin:
            return False, 'hora_inicio (debe ser anterior a hora_termino)'
    except ValueError:
        return False, 'hora_inicio o hora_termino (formato inválido)'

    # Peso
    try:
        peso = float(form.get('peso', '0').strip() or '0')
        if peso != 0 and peso <= 0:
            return False, 'peso (debe ser positivo)'
    except ValueError:
        return False, 'peso (no numérico)'

    # Talla
    try:
        talla = float(form.get('talla', '0').strip() or '0')
        if talla != 0 and talla <= 0:
            return False, 'talla (debe ser positiva)'
    except ValueError:
        return False, 'talla (no numérico)'

    # TA sistólica
    try:
        sistolica = int(form.get('ta_sistolica', '0').strip() or '0')
        if sistolica != 0 and sistolica < 50:
            return False, 'ta_sistolica (valor bajo)'
    except ValueError:
        return False, 'ta_sistolica (no numérico)'

    # TA diastólica
    try:
        diastolica = int(form.get('ta_diastolica', '0').strip() or '0')
        if diastolica != 0 and diastolica < 30:
            return False, 'ta_diastolica (valor bajo)'
    except ValueError:
        return False, 'ta_diastolica (no numérico)'

    # Glucosa
    try:
        glucosa = int(form.get('glucosa', '0').strip() or '0')
        if glucosa != 0 and glucosa < 40:
            return False, 'glucosa (valor bajo)'
    except ValueError:
        return False, 'glucosa (no numérico)'

    # Frecuencia cardiaca (fc)
    try:
        fc = int(form.get('fc', '0').strip() or '0')
        if fc != 0 and fc < 0:
            return False, 'fc (debe ser positivo)'
    except ValueError:
        return False, 'fc (no numérico)'

    # Frecuencia respiratoria (fcr)
    try:
        fcr = int(form.get('fcr', '0').strip() or '0')
        if fcr != 0 and fcr < 0:
            return False, 'fcr (debe ser positivo)'
    except ValueError:
        return False, 'fcr (no numérico)'

    # Temperatura
    try:
        temperatura = float(form.get('temperatura', '0').strip() or '0')
        if temperatura != 0 and temperatura < 30:
            return False, 'temperatura (rango inválido)'
    except ValueError:
        return False, 'temperatura (no numérico)'

    # Circunferencia (circo)
    try:
        circo = float(form.get('circo', '0').strip() or '0')
        if circo != 0 and circo < 0:
            return False, 'circo (debe ser positivo)'
    except ValueError:
        return False, 'circo (no numérico)'

    # IMC
    try:
        imc = float(form.get('imc', '0').strip() or '0')
        if imc != 0 and imc <= 0:
            return False, 'imc (debe ser positivo)'
    except ValueError:
        return False, 'imc (no numérico)'

    # Saturación
    try:
        spo2 = int(form.get('saturacion', '0').strip() or '0')
        if spo2 != 0 and spo2 < 85:
            return False, 'saturación (valor bajo)'
    except ValueError:
        return False, 'saturación (no numérico)'

    return True, ''
