from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, RolSistema

# Cambia esta URL según tu configuración de base de datos
engine = create_engine("postgresql://postgres:dpgtdes@localhost:5432/consultoria_pruebas")
Session = sessionmaker(bind=engine)
session = Session()

# Crear los roles si no existen
roles_iniciales = [
    {'nombre_rol': 'admin', 'descripcion': 'Acceso total al sistema'},
    {'nombre_rol': 'archivo', 'descripcion': 'Módulo de archivo clínico'},
    {'nombre_rol': 'farmacia', 'descripcion': 'Módulo de farmacia'},
    {'nombre_rol': 'enfermeria', 'descripcion': 'Módulo de enfermería'},
]

for rol in roles_iniciales:
    existe = session.query(RolSistema).filter_by(nombre_rol=rol['nombre_rol']).first()
    if not existe:
        nuevo_rol = RolSistema(nombre_rol=rol['nombre_rol'], descripcion=rol['descripcion'])
        session.add(nuevo_rol)

session.commit()
print("Roles insertados correctamente.")
