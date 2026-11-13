# =============================================================================
# INSTITUCIÓN: IFTS N° 4
# CARRERA: Tecnicatura Superior en Desarrollo de Software
# MATERIA: Programación sobre Redes
# PROFESOR: Javier Blanco
# ALUMNO: Luis Segundo Ojeda
# TRABAJO PRÁCTICO: Trabajo Práctico Integrador Final
# ARCHIVO: conexion_bd.py
# DESCRIPCIÓN: 
#   Módulo de persistencia y capa de acceso a datos para MySQL (XAMPP).
#   Contiene las funciones para establecer conexiones mediante mysql-connector,
#   asegurar la existencia de la base de datos y sus tablas ('usuarios' y 'followers'),
#   validar las credenciales de los clientes que inician sesión y persistir
#   los seguidores consultados a través del comando /followers.
# =============================================================================

# -----------------------------------------------------------------------------
# 1. IMPORTACIÓN DE MÓDULOS DE SISTEMA Y CONTROLADOR DE BASE DE DATOS
# -----------------------------------------------------------------------------
import os
import time
import subprocess

# Controlador oficial de Oracle para conectar aplicaciones Python con MySQL
import mysql.connector
from mysql.connector import errorcode

# -----------------------------------------------------------------------------
# 2. PARÁMETROS DE CONFIGURACIÓN DE CONEXIÓN A MYSQL
# -----------------------------------------------------------------------------
# Configuramos los parámetros por defecto de la distribución XAMPP:
# - Servidor local: localhost (127.0.0.1)
# - Puerto estándar MySQL: 3306
# - Usuario administrador por defecto: 'root'
# - Contraseña en blanco: ''
# - Base de datos del proyecto: 'db_github_api'
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "db_github_api"
}


# -----------------------------------------------------------------------------
# 3. FUNCIÓN DE CONEXIÓN CON CONTROL DE EXCEPCIONES
# -----------------------------------------------------------------------------
def connect_db():
    """
    Establece y retorna un objeto de conexión activo hacia la base de datos MySQL.
    Captura y clasifica los posibles códigos de error devueltos por el motor:
      - ER_ACCESS_DENIED_ERROR: credenciales incorrectas en db_config.
      - ER_BAD_DB_ERROR: la base de datos 'db_github_api' aún no ha sido creada.
    Retorna None en caso de fallo para permitir el manejo seguro en capas superiores.
    """
    try:
        # mysql.connector.connect desempaqueta el diccionario db_config con **
        conexion = mysql.connector.connect(**db_config)
        return conexion
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("[ERROR BD]: Usuario o contraseña de MySQL incorrectos.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("[ERROR BD]: La base de datos 'db_github_api' no existe aún.")
        else:
            print(f"[ERROR BD]: Ocurrió un error al conectar con MySQL: {err}")
        return None


# -----------------------------------------------------------------------------
# 4. INICIALIZACIÓN AUTOMÁTICA DE LA BASE DE DATOS Y TABLA USUARIOS (DDL + DML)
# -----------------------------------------------------------------------------
def inicializar_bd_si_no_existe():
    """
    Garantiza la disponibilidad inmediata del entorno de datos.
    1. Si el servicio de MySQL en XAMPP no está corriendo pero existe en el disco,
       intenta iniciarlo en segundo plano.
    2. Se conecta al motor MySQL (sin especificar base de datos) para crear
       la base 'db_github_api' si aún no fue creada ni importada desde phpMyAdmin.
    3. Crea la tabla 'usuarios' mediante CREATE TABLE IF NOT EXISTS.
    4. Inserta usuarios de prueba precargados utilizando INSERT IGNORE para
       evitar duplicados en reinicios sucesivos del servidor.
    Retorna True si la base y la tabla están listas, o False si falló la conexión.
    """
    # Verificación previa: comprobamos si el puerto 3306 responde
    try:
        conexion_prueba = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"]
        )
        conexion_prueba.close()
    except mysql.connector.Error:
        # Si falla la conexión, intentamos iniciar el ejecutable de MySQL de XAMPP si existe en C:\xampp
        ruta_mysqld = r"C:\xampp\mysql\bin\mysqld.exe"
        ruta_ini = r"C:\xampp\mysql\bin\my.ini"
        if os.path.exists(ruta_mysqld):
            print("Detectado XAMPP instalado. Iniciando servicio mysqld.exe en segundo plano...")
            try:
                bandera_oculto = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                subprocess.Popen([ruta_mysqld, f"--defaults-file={ruta_ini}"], creationflags=bandera_oculto)
                # Pausa de espera de 2.5 segundos para que el motor inicialice sockets y buffers
                time.sleep(2.5)
            except Exception as e_proc:
                print(f"No se pudo arrancar mysqld automáticamente: {e_proc}")

    # Proceso formal de creación y verificación DDL
    try:
        # Paso A: Conexión al motor MySQL sin definir base de datos para ejecutar DDL de creación
        conexion_maestra = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"]
        )
        cursor = conexion_maestra.cursor()

        # Paso B: Creación de la base de datos del proyecto
        cursor.execute("CREATE DATABASE IF NOT EXISTS db_github_api")
        cursor.execute("USE db_github_api")

        # Paso C: Tabla 'usuarios' para la validación de login
        # Campos: id (clave primaria autoincremental), username (único), password
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(50) NOT NULL
            )
        """)

        # Paso D: Tabla 'repositorios' (para persistencia de repositorios)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositorios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150),
                html_url VARCHAR(255)
            )
        """)

        # Paso E: Tabla 'followers' para persistir el comando /followers (API de GitHub)
        # Campos: id (clave primaria), login (nombre de usuario seguidor), html_url (URL de perfil)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                login VARCHAR(100),
                html_url VARCHAR(255)
            )
        """)

        # Paso F: Poblado inicial de usuarios de prueba (DML con INSERT IGNORE)
        # Permite probar la concurrencia abriendo múltiples clientes en simultáneo
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password) VALUES
            ('alumno', '1234'),
            ('javier', '1234'),
            ('cliente1', '1234'),
            ('cliente2', '1234'),
            ('operador', 'admin')
        """)

        # Confirmamos la transacción en el motor de base de datos
        conexion_maestra.commit()
        
        # Liberamos cursor y conexión inicial
        cursor.close()
        conexion_maestra.close()
        
        print("[BD]: Base de datos 'db_github_api', tablas 'usuarios' y 'followers' verificadas correctamente.")
        return True

    except mysql.connector.Error as err:
        print(f"[BD ERROR]: Error al inicializar la base de datos en MySQL: {err}")
        return False


# -----------------------------------------------------------------------------
# 5. VALIDACIÓN DE CREDENCIALES DE CLIENTE
# -----------------------------------------------------------------------------
def validar_usuario(username, password):
    """
    Consulta la tabla 'usuarios' para verificar si existe una coincidencia
    exacta entre el nombre de usuario y la contraseña provistos en el login.
    Utiliza consultas parametrizadas con placeholders (%s) como buena práctica
    profesional de software para prevenir inyecciones SQL (SQL Injection).
    Retorna True si el usuario existe y las credenciales coinciden, False en caso contrario.
    """
    conexion = connect_db()
    if conexion is None:
        return False

    try:
        cursor = conexion.cursor()
        # Consulta SELECT parametrizada
        query = "SELECT id FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        
        # fetchone() recupera la primera fila coincidente
        registro = cursor.fetchone()
        
        cursor.close()
        conexion.close()

        # Si registro tiene datos, la autenticación es válida
        return registro is not None

    except Exception as error_select:
        print(f"[BD ERROR]: Error al validar credenciales para '{username}': {error_select}")
        return False


# -----------------------------------------------------------------------------
# 6. PERSISTENCIA DE REPOSITORIOS DE GITHUB
# -----------------------------------------------------------------------------
def guardar_repositorios_bd(lista_repos):
    """
    Recibe la lista de repositorios obtenida desde la API REST de GitHub.
    Extrae 'name' y 'html_url' y los inserta en la tabla 'repositorios'.
    Retorna la cantidad entera de registros insertados exitosamente.
    """
    conexion = connect_db()
    if conexion is None:
        return 0

    cantidad_insertados = 0
    try:
        cursor = conexion.cursor()
        query_insert = "INSERT INTO repositorios (name, html_url) VALUES (%s, %s)"
        for repo in lista_repos:
            cursor.execute(query_insert, (repo.get("name", ""), repo.get("html_url", "")))
            cantidad_insertados += 1
        conexion.commit()
        cursor.close()
        conexion.close()
        return cantidad_insertados
    except Exception as error_insert:
        print(f"[BD ERROR]: Error al insertar repositorios: {error_insert}")
        return cantidad_insertados


# -----------------------------------------------------------------------------
# 7. PERSISTENCIA DE SEGUIDORES DE GITHUB (COMANDO /followers)
# -----------------------------------------------------------------------------
def guardar_followers_bd(lista_followers):
    """
    Recibe la lista de seguidores obtenida desde la API REST de GitHub
    en el endpoint '/users/<usuario>/followers'.
    Extrae los campos requeridos ('login' y 'html_url') y los inserta en la
    tabla 'followers' de la base de datos utilizando consultas parametrizadas.
    Retorna la cantidad entera de registros insertados exitosamente.
    """
    conexion = connect_db()
    if conexion is None:
        return 0

    cantidad_insertados = 0
    try:
        cursor = conexion.cursor()
        query_insert = "INSERT INTO followers (login, html_url) VALUES (%s, %s)"

        for seguidor in lista_followers:
            login_seguidor = seguidor.get("login", "")
            url_seguidor = seguidor.get("html_url", "")

            cursor.execute(query_insert, (login_seguidor, url_seguidor))
            cantidad_insertados += 1

        # Confirmamos la transacción
        conexion.commit()
        cursor.close()
        conexion.close()

        return cantidad_insertados

    except Exception as error_insert:
        print(f"[BD ERROR]: Error al insertar seguidores en la tabla: {error_insert}")
        return cantidad_insertados
