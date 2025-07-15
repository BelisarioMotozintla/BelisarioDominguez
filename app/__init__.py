from flask import Flask
import os
from config import DevelopmentConfig
from .utils.db import db, crear_base_datos

def create_app():
    app = Flask(__name__)
    app.config.from_object(DevelopmentConfig)

    # Inicializar db una sola vez
    #engine_options = app.config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
    #db.init_app(app, engine_options=engine_options)
    db.init_app(app)

    with app.app_context():
        crear_base_datos()

    app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.routes import auth, admin, formulario, formatos, tutorial
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(formulario.bp)
    app.register_blueprint(formatos.bp)
    app.register_blueprint(tutorial.bp)


    return app
