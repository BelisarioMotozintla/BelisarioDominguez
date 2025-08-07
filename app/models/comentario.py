# app/models/comentario.py
from datetime import datetime
from app.utils.db import db

class Comentario(db.Model):
    __tablename__ = 'Comentario'
    id = db.Column(db.Integer, primary_key=True)
    autor = db.Column(db.String(100), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
