from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

db = SQLAlchemy()  # Instancia global

def crear_base_datos():
    from app.models.personal import Usuario, Roles  # Importar aquí para evitar import circular
    print("Creando base de datos y tablas...")
    db.create_all()

    print("Insertando roles...")
    roles_definidos = [
        (4, "Administrador", "Acceso total y gestión de usuarios"),
        (5, "UsuarioEnfermeria", "Acceso a enfermería."),
        (6, "UsuarioAdministrativo", "Acceso a farmacia y archivo clínico"),
        (7, "UsuarioAdmin", "Acceso y control de submódulos de personal"),
        (8, "SuperUsuario", "Acceso a todos los módulos, incluido personal y configuración"),
    ]

    # Insertar roles si no existen
    for id_rol, nombre_rol, descripcion in roles_definidos:
        if not Roles.query.filter_by(nombre_rol=nombre_rol).first():
            rol = Roles(id_rol=id_rol, nombre_rol=nombre_rol, descripcion=descripcion)
            db.session.add(rol)

    db.session.commit()


    # Crear un usuario para cada rol si no existe
    for _, nombre_rol, _ in roles_definidos:
        nombre_usuario = nombre_rol.upper()  # Ej. ADMINISTRADOR
        if not Usuario.query.filter_by(usuario=nombre_usuario).first():
            rol = Roles.query.filter_by(nombre_rol=nombre_rol).first()
            nuevo_usuario = Usuario(
                usuario=nombre_usuario,
                contrasena_hash=generate_password_hash("1234"),  # Contraseña genérica
                rol=rol
            )
            db.session.add(nuevo_usuario)

    db.session.commit()


