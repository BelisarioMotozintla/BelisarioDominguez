from datetime import datetime

def campos_validos(form):
    # Campos que no pueden estar vacíos
    campos_obligatorios = ['unidad_salud', 'fecha', 'hora_inicio', 'hora_termino', 'edad']

    # Validar que campos obligatorios no estén vacíos
    for campo in campos_obligatorios:
        valor = form.get(campo, '').strip()
        if valor == '':
            return False, campo

    # Validar edad: debe ser entero positivo
    try:
        edad = int(form.get('edad', '').strip())
        if edad < 0:
            return False, 'edad (valor no válido)'
    except ValueError:
        return False, 'edad (no numérico)'

    # Validar fecha: formato y que no sea futura
    try:
        fecha = datetime.strptime(form.get('fecha', '').strip(), '%Y-%m-%d')
        if fecha > datetime.now():
            return False, 'fecha (futura)'
    except ValueError:
        return False, 'fecha (formato inválido)'

    # Validar horas: formato correcto y hora_inicio < hora_termino
    try:
        inicio = datetime.strptime(form.get('hora_inicio', ''), '%H:%M')
        fin = datetime.strptime(form.get('hora_termino', ''), '%H:%M')
        if inicio >= fin:
            return False, 'hora_inicio (debe ser anterior a hora_termino)'
    except ValueError:
        return False, 'hora_inicio o hora_termino (formato inválido)'

    return True, None
