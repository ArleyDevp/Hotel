from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reservas = db.relationship('Reserva', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Cliente(db.Model):
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    documento_identidad = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.String(200))
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    reservas = db.relationship('Reserva', backref='cliente', lazy=True)

class Habitacion(db.Model):
    __tablename__ = 'habitaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    precio_por_noche = db.Column(db.Float, nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    piso = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='disponible')
    imagen_url = db.Column(db.String(200))
    
    reservas = db.relationship('Reserva', backref='habitacion', lazy=True)
    
    @property
    def esta_disponible(self):
        return self.estado == 'disponible'
    
    def get_imagen_url(self):
        if self.imagen_url:
            return self.imagen_url
        imagenes = {
            'individual': '/static/images/room-standard.jpg',
            'doble': '/static/images/room-standard.jpg',
            'suite': '/static/images/room-suite.jpg',
            'suite_lujo': '/static/images/room-deluxe.jpg',
            'familiar': '/static/images/room-suite.jpg'
        }
        return imagenes.get(self.tipo, '/static/images/room-standard.jpg')

class Reserva(db.Model):
    __tablename__ = 'reservas'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    habitacion_id = db.Column(db.Integer, db.ForeignKey('habitaciones.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    fecha_entrada = db.Column(db.Date, nullable=False)
    fecha_salida = db.Column(db.Date, nullable=False)
    num_huespedes = db.Column(db.Integer, nullable=False)
    estado = db.Column(db.String(20), default='confirmada')
    total = db.Column(db.Float, nullable=False)
    metodo_pago = db.Column(db.String(50))
    notas = db.Column(db.Text)
    fecha_reserva = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def noches(self):
        return (self.fecha_salida - self.fecha_entrada).days
    
    @property
    def esta_activa(self):
        hoy = datetime.now().date()
        return self.fecha_entrada <= hoy <= self.fecha_salida
