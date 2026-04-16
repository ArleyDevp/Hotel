from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, DateField, IntegerField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo, ValidationError
from models import User, Cliente, Habitacion, Reserva
from datetime import date

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Iniciar Sesión')

class RegisterForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar Contraseña', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Este nombre de usuario ya está en uso.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Este email ya está en uso.')

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono', validators=[DataRequired(), Length(min=7, max=20)])
    documento_identidad = StringField('Documento de Identidad', validators=[DataRequired(), Length(min=5, max=20)])
    direccion = StringField('Dirección', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Guardar Cliente')

class HabitacionForm(FlaskForm):
    numero = StringField('Número de Habitación', validators=[DataRequired(), Length(min=1, max=10)])
    tipo = SelectField('Tipo de Habitación', choices=[
        ('individual', 'Individual'),
        ('doble', 'Doble'),
        ('suite', 'Suite'),
        ('suite_lujo', 'Suite de Lujo'),
        ('familiar', 'Familiar')
    ], validators=[DataRequired()])
    descripcion = TextAreaField('Descripción', validators=[Optional()])
    precio_por_noche = FloatField('Precio por Noche', validators=[DataRequired(), NumberRange(min=0)])
    capacidad = IntegerField('Capacidad', validators=[DataRequired(), NumberRange(min=1, max=10)])
    piso = IntegerField('Piso', validators=[DataRequired(), NumberRange(min=1, max=50)])
    estado = SelectField('Estado', choices=[
        ('disponible', 'Disponible'),
        ('mantenimiento', 'En Mantenimiento'),
        ('ocupada', 'Ocupada')
    ], validators=[DataRequired()])
    imagen_url = StringField('URL de Imagen', validators=[Optional()])
    submit = SubmitField('Guardar Habitación')
    
    def validate_numero(self, numero):
        habitacion = Habitacion.query.filter_by(numero=numero.data).first()
        if habitacion:
            raise ValidationError('Este número de habitación ya existe.')

class ReservaForm(FlaskForm):
    cliente_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    habitacion_id = SelectField('Habitación', coerce=int, validators=[DataRequired()])
    fecha_entrada = DateField('Fecha de Entrada', validators=[DataRequired()], format='%Y-%m-%d')
    fecha_salida = DateField('Fecha de Salida', validators=[DataRequired()], format='%Y-%m-%d')
    num_huespedes = IntegerField('Número de Huéspedes', validators=[DataRequired(), NumberRange(min=1, max=10)])
    metodo_pago = SelectField('Método de Pago', choices=[
        ('efectivo', 'Efectivo'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('transferencia', 'Transferencia'),
        ('paypal', 'PayPal')
    ], validators=[DataRequired()])
    notas = TextAreaField('Notas', validators=[Optional()])
    submit = SubmitField('Realizar Reserva')
    
    def validate_fecha_entrada(self, fecha_entrada):
        if fecha_entrada.data < date.today():
            raise ValidationError('La fecha de entrada no puede ser en el pasado.')
    
    def validate_fecha_salida(self, fecha_salida):
        if self.fecha_entrada.data and fecha_salida.data <= self.fecha_entrada.data:
            raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')

class ReservaPublicaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(min=2, max=100)])
    apellido = StringField('Apellido', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    telefono = StringField('Teléfono', validators=[DataRequired(), Length(min=7, max=20)])
    documento_identidad = StringField('Documento de Identidad', validators=[DataRequired(), Length(min=5, max=20)])
    fecha_entrada = DateField('Fecha de Entrada', validators=[DataRequired()], format='%Y-%m-%d')
    fecha_salida = DateField('Fecha de Salida', validators=[DataRequired()], format='%Y-%m-%d')
    num_huespedes = IntegerField('Número de Huéspedes', validators=[DataRequired(), NumberRange(min=1, max=10)])
    num_habitacion = StringField('Número de Habitación', validators=[DataRequired()])
    submit = SubmitField('Reservar')
    
    def validate_fecha_entrada(self, fecha_entrada):
        if fecha_entrada.data < date.today():
            raise ValidationError('La fecha de entrada no puede ser en el pasado.')
    
    def validate_fecha_salida(self, fecha_salida):
        if self.fecha_entrada.data and fecha_salida.data <= self.fecha_entrada.data:
            raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')
