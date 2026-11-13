-- ============================================================================
-- TP Integrador Final - Programación sobre Redes
-- Institución: IFTS N° 4
-- Script de creación de Base de Datos MySQL (para XAMPP / phpMyAdmin)
-- Base de datos: db_github_api
-- ============================================================================

CREATE DATABASE IF NOT EXISTS db_github_api;
USE db_github_api;

-- Tabla de usuarios para validar el login de los clientes al conectarse
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(50) NOT NULL
);

-- Tabla para almacenar los repositorios consultados con el comando /repos
CREATE TABLE IF NOT EXISTS repositorios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150),
    html_url VARCHAR(255)
);

-- Tabla para almacenar los seguidores consultados con el comando /followers
CREATE TABLE IF NOT EXISTS followers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login VARCHAR(100),
    html_url VARCHAR(255)
);

-- Usuarios de prueba precargados para verificar clientes concurrentes
INSERT IGNORE INTO usuarios (username, password) VALUES 
('alumno', '1234'),
('javier', '1234'),
('cliente1', '1234'),
('cliente2', '1234'),
('operador', 'admin');
