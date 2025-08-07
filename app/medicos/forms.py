from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    usuario = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar sesión')

class SolicitudForm(FlaskForm):
    nombre = StringField('Nombre del paciente', validators=[DataRequired()])
    tipo = SelectField('Tipo de paciente', choices=[('foraneo', 'Foráneo'), ('universo', 'Universo')])
    programa = SelectField('Programa', choices=[
        ('planificacion', 'Planificación Familiar'),
        ('hipertensos', 'Hipertensos'),
        ('diabeticos', 'Diabéticos'),
        ('metabolico', 'Metabólico'),
        ('embarazadas', 'Embarazadas')
    ])
    solicitado_por = SelectField('Solicitado por', choices=[
        ('paciente', 'Paciente'),
        ('medico', 'Médico'),
        ('gestion', 'Gestión de Calidad')
    ])
    submit = SubmitField('Registrar solicitud')
