from flask import Flask,session
import os
from config import DevelopmentConfig
from .utils.db import db, crear_base_datos
from app.utils.extensions import login_manager


def create_app():
    # 🔁 Importar todos los modelos para registrarlos
    from app import models
    from app.models.archivo_clinico import UnidadSalud, Paciente, PacienteUnidad, ArchivoClinico, SolicitudExpediente
    from app.models.personal import Usuario, Roles, Empleado, Turno, Puesto, Servicio, Estudios
    from app.models.farmacia import Medicamento, EntradaAlmacen, MovimientoAlmacenFarmacia, SalidaFarmaciaPaciente, TransferenciaSaliente, TransferenciaEntrante, InventarioAlmacen, InventarioFarmacia, RangoFolios, RecetaMedica, DetalleReceta, BitacoraAccion, BitacoraMovimiento
    from app.models.enfermeria import RegistroAdultoMayor, Archivo
    from app.models.comentario import Comentario
    from app.models.medicos import NotaConsultaExterna

    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(DevelopmentConfig)
    
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Ruta para login si usuario no autenticado
    
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    @app.context_processor
    def inject_usuario():
        return dict(usuario=session.get('usuario'))

    # ✅ Inicializar SQLAlchemy con la app
    db.init_app(app)

    with app.app_context():
        # 🧠 Confirmar que modelos estén registrados
        print("\n--- CLASES REGISTRADAS POR SQLALCHEMY ---")
        for name, cls in db.Model.registry._class_registry.items():
            if "Paciente" in str(name) or "Paciente" in str(cls):
                print(f"{name}: {cls}")
        print("--- FIN DEL REGISTRO ---\n")

        print("Endpoints registrados:")
        for rule in app.url_map.iter_rules():
       		print(f"{rule.endpoint} -> {rule.rule}")

        # ✅ Crear tablas
        crear_base_datos()

    # 📁 Configurar carpeta de uploads
    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 🔧 Registrar blueprints
    from app.main import bp as main_bp
    from app.auth import auth_bp
    from app.enfermeria import enfermeria_bp
    from app.archivo_clinico import archivo_clinico_bp
    from app.paciente import paciente_bp
    from app.farmacia import farmacia_bp
    from app.personal import personal_bp
    from app.admin import admin_bp
    from app.formatos import formatos_bp
    from app.comentario import comentario_bp
    from app.medicos import medicos_bp


    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(enfermeria_bp, url_prefix='/enfermeria')
    app.register_blueprint(archivo_clinico_bp, url_prefix='/archivo')
    app.register_blueprint(paciente_bp, url_prefix='/paciente')
    app.register_blueprint(farmacia_bp, url_prefix='/farmacia')
    app.register_blueprint(personal_bp, url_prefix='/personal')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(formatos_bp, url_prefix='/formatos')
    app.register_blueprint(comentario_bp, url_prefix='/comentario')
    app.register_blueprint(medicos_bp, url_prefix='/medicos')

    app.register_blueprint(main_bp)
    
    print("Endpoints registrados:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint} -> {rule.rule}")

    return app
