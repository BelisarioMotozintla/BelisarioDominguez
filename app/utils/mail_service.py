from flask_mail import Message
from app import mail  # Importa mail desde donde se inicializó


def enviar_correo_confirmacion(email, mensaje,subjectp):
    if not email:
        return

    msg = Message(
        subject=subjectp,
        sender="belisario.dominguez.calidad@gmail.com",
        recipients=[email]
    )

    msg.body = mensaje

    try:
        mail.send(msg)
        print("Correo enviado correctamente")
    except Exception as e:
        print("Error enviando correo:", e)
