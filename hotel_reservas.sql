-- =============================================
-- SCRIPT SQL PARA BASE DE DATOS HOTEL_RESERVAS
-- MySQL 8.0+
-- =============================================

-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS hotel_reservas 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE hotel_reservas;

-- =============================================
-- TABLA DE USUARIOS (ADMINISTRADORES)
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB;

-- =============================================
-- TABLA DE CLIENTES
-- =============================================
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    documento_identidad VARCHAR(20) NOT NULL,
    direccion VARCHAR(200),
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_documento (documento_identidad),
    INDEX idx_apellido (apellido)
) ENGINE=InnoDB;

-- =============================================
-- TABLA DE HABITACIONES
-- =============================================
CREATE TABLE IF NOT EXISTS habitaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE,
    tipo VARCHAR(50) NOT NULL,
    descripcion TEXT,
    precio_por_noche FLOAT NOT NULL,
    capacidad INT NOT NULL,
    piso INT NOT NULL,
    estado VARCHAR(20) DEFAULT 'disponible',
    imagen_url VARCHAR(200),
    INDEX idx_numero (numero),
    INDEX idx_tipo (tipo),
    INDEX idx_estado (estado)
) ENGINE=InnoDB;

-- =============================================
-- TABLA DE RESERVAS
-- =============================================
CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    habitacion_id INT NOT NULL,
    user_id INT NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    num_huespedes INT NOT NULL,
    estado VARCHAR(20) DEFAULT 'confirmada',
    total FLOAT NOT NULL,
    metodo_pago VARCHAR(50),
    notas TEXT,
    fecha_reserva DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
    FOREIGN KEY (habitacion_id) REFERENCES habitaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_fecha_entrada (fecha_entrada),
    INDEX idx_fecha_salida (fecha_salida),
    INDEX idx_estado (estado)
) ENGINE=InnoDB;

-- =============================================
-- DATOS DE PRUEBA: USUARIO ADMIN
-- Contraseña: admin123 (hash generado con werkzeug)
-- =============================================
INSERT INTO users (username, email, password_hash, is_admin) VALUES 
('admin', 'admin@hotel.com', 'scrypt:32768:8:1$salt$hash', TRUE)
ON DUPLICATE KEY UPDATE username = username;

-- Nota: Para crear el hash correcto, ejecutar desde Python:
-- from werkzeug.security import generate_password_hash
-- print(generate_password_hash('admin123'))

-- Para usuarios nuevos, usar el endpoint de registro de la app

-- =============================================
-- DATOS DE PRUEBA: HABITACIONES
-- =============================================
INSERT INTO habitaciones (numero, tipo, descripcion, precio_por_noche, capacidad, piso, estado) VALUES
('101', 'individual', 'Habitación individual cómoda con baño privado', 50.00, 1, 1, 'disponible'),
('102', 'individual', 'Habitación individual con vista al jardín', 55.00, 1, 1, 'disponible'),
('201', 'doble', 'Habitación doble con cama Queen', 80.00, 2, 2, 'disponible'),
('202', 'doble', 'Habitación doble con camas gemelas', 75.00, 2, 2, 'disponible'),
('301', 'suite', 'Suite elegante con sala de estar', 120.00, 2, 3, 'disponible'),
('401', 'suite_lujo', 'Suite de lujo con jacuzzi privado', 200.00, 2, 4, 'disponible'),
('501', 'familiar', 'Habitación familiar con 2 camas dobles', 150.00, 4, 5, 'disponible')
ON DUPLICATE KEY UPDATE numero = numero;

-- =============================================
-- DATOS DE PRUEBA: CLIENTES
-- =============================================
INSERT INTO clientes (nombre, apellido, email, telefono, documento_identidad, direccion) VALUES
('Juan', 'Pérez', 'juan.perez@email.com', '+1234567890', '12345678A', 'Calle Principal 123'),
('María', 'García', 'maria.garcia@email.com', '+1234567891', '87654321B', 'Avenida Secundaria 456')
ON DUPLICATE KEY UPDATE documento_identidad = documento_identidad;

-- =============================================
-- CONSULTAS ÚTILES
-- =============================================

-- Ver todas las reservas activas
-- SELECT r.*, c.nombre, c.apellido, h.numero 
-- FROM reservas r 
-- JOIN clientes c ON r.cliente_id = c.id 
-- JOIN habitaciones h ON r.habitacion_id = h.id 
-- WHERE r.fecha_entrada <= CURDATE() AND r.fecha_salida >= CURDATE();

-- Ver habitaciones disponibles para un rango de fechas
-- SELECT h.* FROM habitaciones h 
-- WHERE h.estado = 'disponible' 
-- AND h.id NOT IN (
--     SELECT r.habitacion_id FROM reservas r 
--     WHERE r.estado != 'cancelada' 
--     AND (r.fecha_entrada <= '2024-12-31' AND r.fecha_salida >= '2024-12-25')
-- );

-- Ver estadísticas del hotel
-- SELECT 
--     (SELECT COUNT(*) FROM reservas) as total_reservas,
--     (SELECT COUNT(*) FROM clientes) as total_clientes,
--     (SELECT COUNT(*) FROM habitaciones) as total_habitaciones,
--     (SELECT COUNT(*) FROM habitaciones WHERE estado = 'disponible') as habitaciones_disponibles;

-- =============================================
-- FIN DEL SCRIPT
-- =============================================
