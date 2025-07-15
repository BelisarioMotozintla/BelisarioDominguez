from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

#db = SQLAlchemy(engine_options=DevelopmentConfig.SQLALCHEMY_ENGINE_OPTIONS)
db = SQLAlchemy()  # Instancia global

def crear_base_datos():
    from app.models import Usuario, RegistroAdultoMayor, Archivo
    db.create_all()

    if not Usuario.query.first():
        admin = Usuario(
            usuario='ADMIN',
            contrasena=generate_password_hash("1234"),  # Sin .encode()
            rol='admin'
        )
        user = Usuario(
            usuario='JUAN',
            contrasena=generate_password_hash("abcd"),  # Sin .encode()
            rol='usuario'
        )
        db.session.add_all([admin, user])
        db.session.commit()

