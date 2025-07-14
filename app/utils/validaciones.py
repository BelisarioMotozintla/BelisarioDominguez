from datetime import datetime

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

    # edad
    try:
        edad = int(form.get('edad', '').strip())
        if edad < 0:
            return False, 'edad (valor no válido)'
    except ValueError:
        return False, 'edad (no numérico)'

    # fecha
    try:
        fecha = datetime.strptime(form.get('fecha', '').strip(), '%Y-%m-%d')
        if fecha > datetime.now():
            return False, 'fecha (futura)'
    except ValueError:
        return False, 'fecha (formato inválido)'

    # hora inicio / termino
    try:
        inicio = datetime.strptime(form.get('hora_inicio', '').strip(), '%H:%M')
        fin = datetime.strptime(form.get('hora_termino', '').strip(), '%H:%M')
        if inicio >= fin:
            return False, 'hora_inicio (debe ser anterior a hora_termino)'
    except ValueError:
        return False, 'hora_inicio o hora_termino (formato inválido)'

    # peso
    try:
        peso = float(form.get('peso', '').strip())
        if peso <= 0:
            return False, 'peso (debe ser positivo)'
    except ValueError:
        return False, 'peso (no numérico)'

    # talla
    try:
        talla = float(form.get('talla', '').strip())
        if talla <= 0:
            return False, 'talla (debe ser positiva)'
    except ValueError:
        return False, 'talla (no numérico)'

    # TA sistólica
    try:
        sistolica = int(form.get('ta_sistolica', '').strip())
        if sistolica < 50:
            return False, 'ta_sistolica (valor bajo)'
    except ValueError:
        return False, 'ta_sistolica (no numérico)'

    # TA diastólica
    try:
        diastolica = int(form.get('ta_diastolica', '').strip())
        if diastolica < 30:
            return False, 'ta_diastolica (valor bajo)'
    except ValueError:
        return False, 'ta_diastolica (no numérico)'

    # glucosa
    try:
        glucosa = int(form.get('glucosa', '').strip())
        if glucosa < 0:
            return False, 'glucosa (debe ser positiva)'
    except ValueError:
        return False, 'glucosa (no numérico)'

    # frecuencia cardiaca (fc)
    try:
        fc = int(form.get('fc', '').strip())
        if fc <= 0:
            return False, 'fc (debe ser positivo)'
    except ValueError:
        return False, 'fc (no numérico)'

    # frecuencia respiratoria (fcr)
    try:
        fcr = int(form.get('fcr', '').strip())
        if fcr <= 0:
            return False, 'fcr (debe ser positivo)'
    except ValueError:
        return False, 'fcr (no numérico)'

    # temperatura
    try:
        temperatura = float(form.get('temperatura', '').strip())
        if not (30 <= temperatura <= 45):
            return False, 'temperatura (rango inválido)'
    except ValueError:
        return False, 'temperatura (no numérico)'

    # circunferencia (HTML: circo)
    try:
        circo = float(form.get('circo', '').strip())
        if circo < 0:
            return False, 'circo (debe ser positivo)'
    except ValueError:
        return False, 'circo (no numérico)'

    # IMC
    try:
        imc = float(form.get('imc', '').strip())
        if imc <= 0:
            return False, 'imc (debe ser positivo)'
    except ValueError:
        return False, 'imc (no numérico)'

    # SPO2
    try:
        spo2 = int(form.get('spo2', '').strip())
        if not (0 <= spo2 <= 100):
            return False, 'spo2 (rango 0-100%)'
    except ValueError:
        return False, 'spo2 (no numérico)'

    return True, None
