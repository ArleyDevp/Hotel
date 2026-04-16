from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Cliente, Habitacion, Reserva
from forms import (LoginForm, RegisterForm, ClienteForm, HabitacionForm, 
                   ReservaForm, ReservaPublicaForm)
from datetime import datetime, date, timedelta
from functools import wraps
import pymysql
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hotel-reservas-secret-key-2024'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '1234'
MYSQL_DATABASE = 'hotel_reservas'

def init_mysql_database():
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()
    finally:
        connection.close()
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}'
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@hotel.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
        if Habitacion.query.count() == 0:
            habitaciones_ejemplo = [
                Habitacion(numero='101', tipo='individual', descripcion='Habitación individual cómoda con baño privado', precio_por_noche=50.0, capacidad=1, piso=1, estado='disponible'),
                Habitacion(numero='102', tipo='individual', descripcion='Habitación individual con vista al jardín', precio_por_noche=55.0, capacidad=1, piso=1, estado='disponible'),
                Habitacion(numero='201', tipo='doble', descripcion='Habitación doble con cama Queen', precio_por_noche=80.0, capacidad=2, piso=2, estado='disponible'),
                Habitacion(numero='202', tipo='doble', descripcion='Habitación doble con camas gemelas', precio_por_noche=75.0, capacidad=2, piso=2, estado='disponible'),
                Habitacion(numero='301', tipo='suite', descripcion='Suite elegante con sala de estar', precio_por_noche=120.0, capacidad=2, piso=3, estado='disponible'),
                Habitacion(numero='401', tipo='suite_lujo', descripcion='Suite de lujo con jacuzzi privado', precio_por_noche=200.0, capacidad=2, piso=4, estado='disponible'),
                Habitacion(numero='501', tipo='familiar', descripcion='Habitación familiar con 2 camas dobles', precio_por_noche=150.0, capacidad=4, piso=5, estado='disponible'),
            ]
            db.session.add_all(habitaciones_ejemplo)
        db.session.commit()
        print("Base de datos MySQL inicializada correctamente.")

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def validar_telefono(telefono):
    patron = r'^[\d\+\-\s\(\)]{7,20}$'
    return re.match(patron, telefono) is not None

def validar_documento(documento):
    if len(documento) < 5 or len(documento) > 20:
        return False
    return True

def verificar_disponibilidad(habitacion_id, fecha_entrada, fecha_salida, reserva_actual_id=None):
    reservas_conflictivas = Reserva.query.filter(
        Reserva.habitacion_id == habitacion_id,
        Reserva.estado != 'cancelada',
        Reserva.fecha_entrada < fecha_salida,
        Reserva.fecha_salida > fecha_entrada
    )
    
    if reserva_actual_id:
        reservas_conflictivas = reservas_conflictivas.filter(Reserva.id != reserva_actual_id)
    
    reserva_conflicto = reservas_conflictivas.first()
    
    if reserva_conflicto:
        return {
            'disponible': False,
            'reserva_conflicto': {
                'fecha_entrada': reserva_conflicto.fecha_entrada.strftime('%Y-%m-%d'),
                'fecha_salida': reserva_conflicto.fecha_salida.strftime('%Y-%m-%d'),
                'cliente': f"{reserva_conflicto.cliente.nombre} {reserva_conflicto.cliente.apellido}"
            }
        }
    
    return {'disponible': True}

@app.route('/api/disponibilidad/<int:habitacion_id>')
def api_disponibilidad(habitacion_id):
    fecha_entrada = request.args.get('fecha_entrada')
    fecha_salida = request.args.get('fecha_salida')
    reserva_id = request.args.get('reserva_id')
    
    if not fecha_entrada or not fecha_salida:
        return jsonify({'error': 'Fechas requeridas'}), 400
    
    try:
        fecha_entrada_dt = datetime.strptime(fecha_entrada, '%Y-%m-%d').date()
        fecha_salida_dt = datetime.strptime(fecha_salida, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido'}), 400
    
    habitacion = Habitacion.query.get_or_404(habitacion_id)
    
    disponibilidad = verificar_disponibilidad(
        habitacion_id, 
        fecha_entrada_dt, 
        fecha_salida_dt,
        int(reserva_id) if reserva_id else None
    )
    
    return jsonify({
        'habitacion_id': habitacion_id,
        'habitacion_numero': habitacion.numero,
        **disponibilidad
    })

@app.route('/api/habitaciones-disponibles')
def api_habitaciones_disponibles():
    fecha_entrada = request.args.get('fecha_entrada')
    fecha_salida = request.args.get('fecha_salida')
    
    if not fecha_entrada or not fecha_salida:
        return jsonify({'error': 'Fechas requeridas'}), 400
    
    try:
        fecha_entrada_dt = datetime.strptime(fecha_entrada, '%Y-%m-%d').date()
        fecha_salida_dt = datetime.strptime(fecha_salida, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido'}), 400
    
    habitaciones = Habitacion.query.all()
    habitaciones_disponibles = []
    
    for h in habitaciones:
        disponibilidad = verificar_disponibilidad(h.id, fecha_entrada_dt, fecha_salida_dt)
        if disponibilidad['disponible']:
            reservas_conflicto = Reserva.query.filter(
                Reserva.habitacion_id == h.id,
                Reserva.estado != 'cancelada',
                Reserva.fecha_salida >= fecha_entrada_dt
            ).order_by(Reserva.fecha_salida.asc()).first()
            
            habitaciones_disponibles.append({
                'id': h.id,
                'numero': h.numero,
                'tipo': h.tipo,
                'precio': h.precio_por_noche
            })
    
    return jsonify(habitaciones_disponibles)

@app.route('/')
def index():
    habitaciones = Habitacion.query.filter_by(estado='disponible').limit(6).all()
    return render_template('index.html', habitaciones=habitaciones)

@app.route('/habitaciones')
def habitaciones():
    tipo = request.args.get('tipo')
    if tipo:
        habitaciones = Habitacion.query.filter_by(tipo=tipo, estado='disponible').all()
    else:
        habitaciones = Habitacion.query.filter_by(estado='disponible').all()
    return render_template('habitaciones.html', habitaciones=habitaciones)

@app.route('/habitacion/<int:id>')
def habitacion_detalle(id):
    habitacion = Habitacion.query.get_or_404(id)
    reservas_proximas = Reserva.query.filter(
        Reserva.habitacion_id == id,
        Reserva.estado != 'cancelada',
        Reserva.fecha_salida >= date.today()
    ).order_by(Reserva.fecha_entrada.asc()).all()
    
    return render_template('habitacion_detalle.html', 
                         habitacion=habitacion, 
                         reservas_proximas=reservas_proximas)

@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    form = ReservaPublicaForm()
    
    if form.validate_on_submit():
        errors = []
        
        nombre = form.nombre.data.strip()
        apellido = form.apellido.data.strip()
        
        if len(nombre) < 2:
            errors.append('El nombre debe tener al menos 2 caracteres')
        if len(apellido) < 2:
            errors.append('El apellido debe tener al menos 2 caracteres')
        
        if not validar_telefono(form.telefono.data):
            errors.append('El formato del teléfono no es válido')
        
        if not validar_documento(form.documento_identidad.data):
            errors.append('El documento de identidad debe tener entre 5 y 20 caracteres')
        
        if not validar_email(form.email.data):
            errors.append('El formato del email no es válido')
        
        if form.fecha_entrada.data < date.today():
            errors.append('La fecha de entrada no puede ser en el pasado')
        
        if form.fecha_salida.data <= form.fecha_entrada.data:
            errors.append('La fecha de salida debe ser posterior a la fecha de entrada')
        
        if (form.fecha_salida.data - form.fecha_entrada.data).days > 30:
            errors.append('La estancia no puede exceder 30 noches')
        
        if form.num_huespedes.data < 1 or form.num_huespedes.data > 10:
            errors.append('El número de huéspedes debe ser entre 1 y 10')
        
        habitacion = Habitacion.query.filter_by(numero=form.num_habitacion.data.strip()).first()
        if not habitacion:
            errors.append('La habitación no existe')
        else:
            disponibilidad = verificar_disponibilidad(
                habitacion.id, 
                form.fecha_entrada.data, 
                form.fecha_salida.data
            )
            
            if not disponibilidad['disponible']:
                conf = disponibilidad['reserva_conflicto']
                errors.append(f'La habitación está ocupada desde el {conf["fecha_entrada"]} hasta el {conf["fecha_salida"]}')
            
            if form.num_huespedes.data > habitacion.capacidad:
                errors.append(f'La capacidad máxima de la habitación es {habitacion.capacidad} personas')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('reservar.html', form=form)
        
        cliente = Cliente.query.filter_by(documento_identidad=form.documento_identidad.data.strip()).first()
        if not cliente:
            cliente = Cliente(
                nombre=nombre,
                apellido=apellido,
                email=form.email.data.strip().lower(),
                telefono=form.telefono.data.strip(),
                documento_identidad=form.documento_identidad.data.strip()
            )
            db.session.add(cliente)
            db.session.commit()
        
        noches = (form.fecha_salida.data - form.fecha_entrada.data).days
        total = noches * habitacion.precio_por_noche
        
        user_id = User.query.filter_by(is_admin=True).first().id
        
        reserva = Reserva(
            cliente_id=cliente.id,
            habitacion_id=habitacion.id,
            user_id=user_id,
            fecha_entrada=form.fecha_entrada.data,
            fecha_salida=form.fecha_salida.data,
            num_huespedes=form.num_huespedes.data,
            total=total,
            metodo_pago='pendiente',
            notas=f'Reservada en línea por {nombre} {apellido}'
        )
        db.session.add(reserva)
        db.session.commit()
        
        flash(f'¡Reserva realizada exitosamente! Habitación {habitacion.numero}, {noches} noche(s). Total: ${total:.2f}', 'success')
        return redirect(url_for('index'))
    
    form.fecha_entrada.data = date.today()
    form.fecha_salida.data = date.today() + timedelta(days=1)
    return render_template('reservar.html', form=form)

def validar_email(email):
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        
        if len(username) < 3:
            flash('El usuario debe tener al menos 3 caracteres', 'danger')
            return render_template('login.html', form=form)
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('login.html', form=form)
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Has iniciado sesión correctamente', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()
        password = form.password.data
        
        if len(username) < 3:
            flash('El usuario debe tener al menos 3 caracteres', 'danger')
            return render_template('register.html', form=form)
        
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
            return render_template('register.html', form=form)
        
        if not validar_email(email):
            flash('El formato del email no es válido', 'danger')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(username=username).first():
            flash('Este nombre de usuario ya está en uso', 'danger')
            return render_template('register.html', form=form)
        
        if User.query.filter_by(email=email).first():
            flash('Este email ya está registrado', 'danger')
            return render_template('register.html', form=form)
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Cuenta creada exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Acceso denegado. Solo administradores.', 'danger')
        return redirect(url_for('index'))
    
    total_reservas = Reserva.query.count()
    total_clientes = Cliente.query.count()
    total_habitaciones = Habitacion.query.count()
    reservas_activas = Reserva.query.filter(
        Reserva.fecha_entrada <= date.today(),
        Reserva.fecha_salida >= date.today(),
        Reserva.estado != 'cancelada'
    ).count()
    
    habitaciones_ocupadas = Habitacion.query.filter_by(estado='ocupada').count()
    
    reservas_recientes = Reserva.query.order_by(Reserva.fecha_reserva.desc()).limit(5).all()
    
    return render_template('admin_dashboard.html', 
                           total_reservas=total_reservas,
                           total_clientes=total_clientes,
                           total_habitaciones=total_habitaciones,
                           reservas_activas=reservas_activas,
                           habitaciones_ocupadas=habitaciones_ocupadas,
                           reservas_recientes=reservas_recientes)

@app.route('/admin/habitaciones')
@login_required
def admin_habitaciones():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    habitaciones = Habitacion.query.order_by(Habitacion.numero).all()
    return render_template('admin_habitaciones.html', habitaciones=habitaciones)

@app.route('/admin/habitacion/nueva', methods=['GET', 'POST'])
@login_required
def admin_habitacion_nueva():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    form = HabitacionForm()
    
    if form.validate_on_submit():
        errors = []
        
        numero = form.numero.data.strip()
        if len(numero) < 1 or len(numero) > 10:
            errors.append('El número de habitación debe tener entre 1 y 10 caracteres')
        
        if Habitacion.query.filter_by(numero=numero).first():
            errors.append('Este número de habitación ya existe')
        
        if form.precio_por_noche.data <= 0:
            errors.append('El precio debe ser mayor a 0')
        
        if form.precio_por_noche.data > 10000:
            errors.append('El precio no puede exceder $10,000 por noche')
        
        if form.capacidad.data < 1 or form.capacidad.data > 20:
            errors.append('La capacidad debe ser entre 1 y 20 personas')
        
        if form.piso.data < 1 or form.piso.data > 100:
            errors.append('El piso debe ser entre 1 y 100')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin_habitacion_form.html', form=form, titulo='Nueva Habitación')
        
        habitacion = Habitacion(
            numero=numero,
            tipo=form.tipo.data,
            descripcion=form.descripcion.data.strip() if form.descripcion.data else '',
            precio_por_noche=form.precio_por_noche.data,
            capacidad=form.capacidad.data,
            piso=form.piso.data,
            estado=form.estado.data,
            imagen_url=form.imagen_url.data.strip() if form.imagen_url.data else None
        )
        db.session.add(habitacion)
        db.session.commit()
        flash('Habitación creada exitosamente', 'success')
        return redirect(url_for('admin_habitaciones'))
    
    return render_template('admin_habitacion_form.html', form=form, titulo='Nueva Habitación')

@app.route('/admin/habitacion/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_habitacion_editar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    habitacion = Habitacion.query.get_or_404(id)
    form = HabitacionForm(obj=habitacion)
    
    if form.validate_on_submit():
        errors = []
        
        numero = form.numero.data.strip()
        habitacion_existente = Habitacion.query.filter_by(numero=numero).first()
        
        if habitacion_existente and habitacion_existente.id != id:
            errors.append('Este número de habitación ya existe')
        
        if len(numero) < 1 or len(numero) > 10:
            errors.append('El número de habitación debe tener entre 1 y 10 caracteres')
        
        if form.precio_por_noche.data <= 0:
            errors.append('El precio debe ser mayor a 0')
        
        if form.precio_por_noche.data > 10000:
            errors.append('El precio no puede exceder $10,000 por noche')
        
        if form.capacidad.data < 1 or form.capacidad.data > 20:
            errors.append('La capacidad debe ser entre 1 y 20 personas')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin_habitacion_form.html', form=form, titulo='Editar Habitación')
        
        habitacion.numero = numero
        habitacion.tipo = form.tipo.data
        habitacion.descripcion = form.descripcion.data.strip() if form.descripcion.data else ''
        habitacion.precio_por_noche = form.precio_por_noche.data
        habitacion.capacidad = form.capacidad.data
        habitacion.piso = form.piso.data
        habitacion.estado = form.estado.data
        habitacion.imagen_url = form.imagen_url.data.strip() if form.imagen_url.data else None
        
        db.session.commit()
        flash('Habitación actualizada exitosamente', 'success')
        return redirect(url_for('admin_habitaciones'))
    
    return render_template('admin_habitacion_form.html', form=form, titulo='Editar Habitación')

@app.route('/admin/habitacion/eliminar/<int:id>')
@login_required
def admin_habitacion_eliminar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    habitacion = Habitacion.query.get_or_404(id)
    
    reservas_activas = Reserva.query.filter(
        Reserva.habitacion_id == id,
        Reserva.estado != 'cancelada',
        Reserva.fecha_entrada <= date.today(),
        Reserva.fecha_salida >= date.today()
    ).count()
    
    if reservas_activas > 0:
        flash('No se puede eliminar una habitación con reservas activas', 'danger')
        return redirect(url_for('admin_habitaciones'))
    
    db.session.delete(habitacion)
    db.session.commit()
    flash('Habitación eliminada', 'warning')
    return redirect(url_for('admin_habitaciones'))

@app.route('/admin/reservas')
@login_required
def admin_reservas():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    estado = request.args.get('estado')
    if estado:
        reservas = Reserva.query.filter_by(estado=estado).order_by(Reserva.fecha_entrada.desc()).all()
    else:
        reservas = Reserva.query.order_by(Reserva.fecha_entrada.desc()).all()
    
    return render_template('admin_reservas.html', reservas=reservas)

@app.route('/admin/reserva/nueva', methods=['GET', 'POST'])
@login_required
def admin_reserva_nueva():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    form = ReservaForm()
    
    clientes = Cliente.query.order_by(Cliente.apellido).all()
    if not clientes:
        flash('Debe registrar al menos un cliente antes de crear una reserva', 'warning')
        return redirect(url_for('admin_cliente_nueva'))
    
    form.cliente_id.choices = [(c.id, f'{c.nombre} {c.apellido} - {c.documento_identidad}') 
                               for c in clientes]
    
    habitaciones_disponibles = []
    for h in Habitacion.query.all():
        reservas_conflicto = Reserva.query.filter(
            Reserva.habitacion_id == h.id,
            Reserva.estado != 'cancelada',
            Reserva.fecha_entrada < date.today() + timedelta(days=365),
            Reserva.fecha_salida > date.today()
        ).order_by(Reserva.fecha_salida.desc()).first()
        
        habitaciones_disponibles.append({
            'id': h.id,
            'numero': h.numero,
            'tipo': h.tipo,
            'precio': h.precio_por_noche,
            'disponible': True,
            'proxima_fecha': reservas_conflicto.fecha_salida.strftime('%Y-%m-%d') if reservas_conflicto else None
        })
    
    if request.method == 'GET':
        form.habitacion_id.choices = [(0, 'Seleccionar habitación')] + [
            (h['id'], f"{h['numero']} - {h['tipo']} (${h['precio']}/noche)") 
            for h in habitaciones_disponibles
        ]
    
    if form.validate_on_submit():
        errors = []
        
        if form.fecha_entrada.data < date.today():
            errors.append('La fecha de entrada no puede ser en el pasado')
        
        if form.fecha_salida.data <= form.fecha_entrada.data:
            errors.append('La fecha de salida debe ser posterior a la fecha de entrada')
        
        if (form.fecha_salida.data - form.fecha_entrada.data).days > 60:
            errors.append('La estancia no puede exceder 60 noches')
        
        if form.num_huespedes.data < 1 or form.num_huespedes.data > 10:
            errors.append('El número de huéspedes debe ser entre 1 y 10')
        
        habitacion = Habitacion.query.get(form.habitacion_id.data)
        if not habitacion:
            errors.append('Debe seleccionar una habitación válida')
        else:
            disponibilidad = verificar_disponibilidad(
                habitacion.id, 
                form.fecha_entrada.data, 
                form.fecha_salida.data
            )
            
            if not disponibilidad['disponible']:
                conf = disponibilidad['reserva_conflicto']
                errors.append(f'La habitación está ocupada del {conf["fecha_entrada"]} al {conf["fecha_salida"]} por {conf["cliente"]}')
            
            if form.num_huespedes.data > habitacion.capacidad:
                errors.append(f'La capacidad máxima de la habitación es {habitacion.capacidad} personas')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            form.habitacion_id.choices = [(0, 'Seleccionar habitación')] + [
                (h['id'], f"{h['numero']} - {h['tipo']} (${h['precio']}/noche)") 
                for h in habitaciones_disponibles
            ]
            return render_template('admin_reserva_form.html', form=form, titulo='Nueva Reserva', 
                                  habitaciones_info=habitaciones_disponibles)
        
        noches = (form.fecha_salida.data - form.fecha_entrada.data).days
        total = noches * habitacion.precio_por_noche
        
        reserva = Reserva(
            cliente_id=form.cliente_id.data,
            habitacion_id=habitacion.id,
            user_id=current_user.id,
            fecha_entrada=form.fecha_entrada.data,
            fecha_salida=form.fecha_salida.data,
            num_huespedes=form.num_huespedes.data,
            total=total,
            metodo_pago=form.metodo_pago.data,
            notas=form.notas.data.strip() if form.notas.data else ''
        )
        
        habitacion.estado = 'ocupada'
        db.session.add(reserva)
        db.session.commit()
        
        flash(f'Reserva creada exitosamente. Total: ${total:.2f}', 'success')
        return redirect(url_for('admin_reservas'))
    
    form.fecha_entrada.data = date.today()
    form.fecha_salida.data = date.today() + timedelta(days=1)
    return render_template('admin_reserva_form.html', form=form, titulo='Nueva Reserva',
                          habitaciones_info=habitaciones_disponibles)

@app.route('/admin/reserva/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_reserva_editar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    reserva = Reserva.query.get_or_404(id)
    form = ReservaForm(obj=reserva)
    
    form.cliente_id.choices = [(c.id, f'{c.nombre} {c.apellido}') 
                               for c in Cliente.query.order_by(Cliente.apellido).all()]
    
    habitaciones_info = []
    for h in Habitacion.query.all():
        disponibilidad = verificar_disponibilidad(h.id, reserva.fecha_entrada, reserva.fecha_salida, id)
        habitacion_ocupada = h.estado == 'ocupada' and not disponibilidad['disponible']
        
        reservas_proximas = Reserva.query.filter(
            Reserva.habitacion_id == h.id,
            Reserva.estado != 'cancelada',
            Reserva.fecha_salida > date.today()
        ).order_by(Reserva.fecha_entrada.asc()).first()
        
        habitaciones_info.append({
            'id': h.id,
            'numero': h.numero,
            'tipo': h.tipo,
            'precio': h.precio_por_noche,
            'capacidad': h.capacidad,
            'disponible': disponibilidad['disponible'] or h.id == reserva.habitacion_id,
            'proxima_fecha': reservas_proximas.fecha_salida.strftime('%Y-%m-%d') if reservas_proximas else None
        })
    
    if request.method == 'GET':
        form.habitacion_id.choices = [(h.id, f'{h.numero} - {h.tipo} (${h.precio_por_noche}/noche)') 
                                      for h in Habitacion.query.all()]
    
    if form.validate_on_submit():
        errors = []
        
        if form.fecha_entrada.data < date.today() - timedelta(days=reserva.fecha_reserva.days_ago if hasattr(reserva.fecha_reserva, 'days_ago') else 0):
            errors.append('La fecha de entrada no puede ser anterior a la fecha de reserva')
        
        if form.fecha_salida.data <= form.fecha_entrada.data:
            errors.append('La fecha de salida debe ser posterior a la fecha de entrada')
        
        if (form.fecha_salida.data - form.fecha_entrada.data).days > 60:
            errors.append('La estancia no puede exceder 60 noches')
        
        if form.num_huespedes.data < 1 or form.num_huespedes.data > 10:
            errors.append('El número de huéspedes debe ser entre 1 y 10')
        
        habitacion = Habitacion.query.get(form.habitacion_id.data)
        if not habitacion:
            errors.append('Debe seleccionar una habitación válida')
        else:
            disponibilidad = verificar_disponibilidad(
                habitacion.id, 
                form.fecha_entrada.data, 
                form.fecha_salida.data,
                id
            )
            
            if not disponibilidad['disponible']:
                conf = disponibilidad['reserva_conflicto']
                errors.append(f'La habitación está ocupada del {conf["fecha_entrada"]} al {conf["fecha_salida"]}')
            
            if form.num_huespedes.data > habitacion.capacidad:
                errors.append(f'La capacidad máxima de la habitación es {habitacion.capacidad} personas')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            form.habitacion_id.choices = [(h.id, f'{h.numero} - {h.tipo}') for h in Habitacion.query.all()]
            return render_template('admin_reserva_form.html', form=form, titulo='Editar Reserva',
                                  habitaciones_info=habitaciones_info)
        
        reserva.cliente_id = form.cliente_id.data
        reserva.habitacion_id = habitacion.id
        reserva.fecha_entrada = form.fecha_entrada.data
        reserva.fecha_salida = form.fecha_salida.data
        reserva.num_huespedes = form.num_huespedes.data
        reserva.metodo_pago = form.metodo_pago.data
        reserva.notas = form.notas.data.strip() if form.notas.data else ''
        
        noches = (form.fecha_salida.data - form.fecha_entrada.data).days
        reserva.total = noches * habitacion.precio_por_noche
        
        db.session.commit()
        flash('Reserva actualizada exitosamente', 'success')
        return redirect(url_for('admin_reservas'))
    
    return render_template('admin_reserva_form.html', form=form, titulo='Editar Reserva',
                          habitaciones_info=habitaciones_info)

@app.route('/admin/reserva/eliminar/<int:id>')
@login_required
def admin_reserva_eliminar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    reserva = Reserva.query.get_or_404(id)
    habitacion = Habitacion.query.get(reserva.habitacion_id)
    
    if reserva.fecha_entrada <= date.today() <= reserva.fecha_salida and reserva.estado == 'confirmada':
        flash('No se puede eliminar una reserva en curso. Cancele la reserva primero.', 'danger')
        return redirect(url_for('admin_reservas'))
    
    habitacion.estado = 'disponible'
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva eliminada', 'warning')
    return redirect(url_for('admin_reservas'))

@app.route('/admin/reserva/estado/<int:id>/<nuevo_estado>')
@login_required
def admin_reserva_estado(id, nuevo_estado):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if nuevo_estado not in ['confirmada', 'pendiente', 'cancelada']:
        flash('Estado inválido', 'danger')
        return redirect(url_for('admin_reservas'))
    
    reserva = Reserva.query.get_or_404(id)
    reserva.estado = nuevo_estado
    
    if nuevo_estado == 'cancelada':
        habitacion = Habitacion.query.get(reserva.habitacion_id)
        habitacion.estado = 'disponible'
        flash('Reserva cancelada. La habitación está disponible.', 'success')
    elif nuevo_estado == 'confirmada':
        habitacion = Habitacion.query.get(reserva.habitacion_id)
        habitacion.estado = 'ocupada'
        flash('Reserva confirmada.', 'success')
    else:
        flash(f'Estado actualizado a {nuevo_estado}', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_reservas'))

@app.route('/admin/clientes')
@login_required
def admin_clientes():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    clientes = Cliente.query.order_by(Cliente.apellido).all()
    return render_template('admin_clientes.html', clientes=clientes)

@app.route('/admin/cliente/nueva', methods=['GET', 'POST'])
@login_required
def admin_cliente_nueva():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    form = ClienteForm()
    
    if form.validate_on_submit():
        errors = []
        
        nombre = form.nombre.data.strip()
        apellido = form.apellido.data.strip()
        
        if len(nombre) < 2:
            errors.append('El nombre debe tener al menos 2 caracteres')
        
        if len(apellido) < 2:
            errors.append('El apellido debe tener al menos 2 caracteres')
        
        if not validar_email(form.email.data):
            errors.append('El formato del email no es válido')
        
        if not validar_telefono(form.telefono.data):
            errors.append('El formato del teléfono no es válido')
        
        if not validar_documento(form.documento_identidad.data):
            errors.append('El documento de identidad debe tener entre 5 y 20 caracteres')
        
        if Cliente.query.filter_by(documento_identidad=form.documento_identidad.data.strip()).first():
            errors.append('Este documento de identidad ya está registrado')
        
        if Cliente.query.filter_by(email=form.email.data.strip().lower()).first():
            errors.append('Este email ya está registrado')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin_cliente_form.html', form=form, titulo='Nuevo Cliente')
        
        cliente = Cliente(
            nombre=nombre,
            apellido=apellido,
            email=form.email.data.strip().lower(),
            telefono=form.telefono.data.strip(),
            documento_identidad=form.documento_identidad.data.strip(),
            direccion=form.direccion.data.strip() if form.direccion.data else ''
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente creado exitosamente', 'success')
        return redirect(url_for('admin_clientes'))
    
    return render_template('admin_cliente_form.html', form=form, titulo='Nuevo Cliente')

@app.route('/admin/cliente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_cliente_editar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    cliente = Cliente.query.get_or_404(id)
    form = ClienteForm(obj=cliente)
    
    if form.validate_on_submit():
        errors = []
        
        nombre = form.nombre.data.strip()
        apellido = form.apellido.data.strip()
        
        if len(nombre) < 2:
            errors.append('El nombre debe tener al menos 2 caracteres')
        
        if len(apellido) < 2:
            errors.append('El apellido debe tener al menos 2 caracteres')
        
        if not validar_email(form.email.data):
            errors.append('El formato del email no es válido')
        
        if not validar_telefono(form.telefono.data):
            errors.append('El formato del teléfono no es válido')
        
        if not validar_documento(form.documento_identidad.data):
            errors.append('El documento de identidad debe tener entre 5 y 20 caracteres')
        
        email_existente = Cliente.query.filter_by(email=form.email.data.strip().lower()).first()
        if email_existente and email_existente.id != id:
            errors.append('Este email ya está registrado por otro cliente')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin_cliente_form.html', form=form, titulo='Editar Cliente')
        
        cliente.nombre = nombre
        cliente.apellido = apellido
        cliente.email = form.email.data.strip().lower()
        cliente.telefono = form.telefono.data.strip()
        cliente.documento_identidad = form.documento_identidad.data.strip()
        cliente.direccion = form.direccion.data.strip() if form.direccion.data else ''
        
        db.session.commit()
        flash('Cliente actualizado exitosamente', 'success')
        return redirect(url_for('admin_clientes'))
    
    return render_template('admin_cliente_form.html', form=form, titulo='Editar Cliente')

@app.route('/admin/cliente/eliminar/<int:id>')
@login_required
def admin_cliente_eliminar(id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    cliente = Cliente.query.get_or_404(id)
    
    reservas_activas = Reserva.query.filter(
        Reserva.cliente_id == id,
        Reserva.estado != 'cancelada',
        Reserva.fecha_salida >= date.today()
    ).count()
    
    if reservas_activas > 0:
        flash(f'No se puede eliminar. El cliente tiene {reservas_activas} reserva(s) activa(s)', 'danger')
        return redirect(url_for('admin_clientes'))
    
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente eliminado', 'warning')
    return redirect(url_for('admin_clientes'))

if __name__ == '__main__':
    init_mysql_database()
    login_manager.init_app(app)
    app.run(debug=True, host='0.0.0.0', port=5000)
