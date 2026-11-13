# =============================================================================
# INSTITUCIÓN: IFTS N° 4
# CARRERA: Tecnicatura Superior en Desarrollo de Software
# MATERIA: Programación sobre Redes
# PROFESOR: Javier Blanco
# ALUMNO: Luis Segundo Ojeda
# TRABAJO PRÁCTICO: Trabajo Práctico Integrador Final
# ARCHIVO: servidor.py
# DESCRIPCIÓN: 
#   Servidor multihilo concurrente implementado con sockets TCP en Python.
#   Escucha peticiones de múltiples clientes simultáneos, realiza la validación
#   de credenciales contra una base de datos MySQL (XAMPP), procesa comandos
#   de red precedidos por "/", consume la API REST de GitHub para persistir
#   información técnica, y provee una interfaz gráfica de administración en Tkinter
#   para monitorear las conexiones y chatear con los clientes conectados.
# =============================================================================

# -----------------------------------------------------------------------------
# 1. IMPORTACIÓN DE MÓDULOS DE LA BIBLIOTECA ESTÁNDAR Y DE TERCEROS
# -----------------------------------------------------------------------------
# El módulo nos brinda utilidades del sistema operativo.
import os

# El módulo socket es la base de las comunicaciones en red bajo la arquitectura TCP/IP.
# Permite crear puntos de enlace (endpoints) para enviar y recibir flujos de bytes.
import socket

# El módulo threading nos permite implementar concurrencia mediante hilos de ejecución.
# Cada cliente que se conecta será atendido por un hilo independiente para no
# bloquear la escucha del servidor ni congelar la interfaz gráfica de usuario.
import threading

# El módulo datetime nos permite obtener marcas temporales (timestamps) para los registros
# y responder al comando específico /hora solicitado en el trabajo práctico.
import datetime

# La librería externa requests se utiliza para realizar peticiones HTTP hacia la API REST
# externa de GitHub (obtención de repositorios públicos y seguidores en formato JSON).
import requests

# Tkinter es la biblioteca gráfica estándar de Python. La utilizamos para construir
# una interfaz de usuario limpia, clara y funcional para el administrador del servidor.
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

# Importamos las funciones desarrolladas en el módulo conexion_bd.py para la interacción
# con la base de datos MySQL (inicialización de tablas, validación e inserciones).
from conexion_bd import (
    inicializar_bd_si_no_existe,
    validar_usuario,
    guardar_repositorios_bd,
    guardar_followers_bd
)

# -----------------------------------------------------------------------------
# 2. CONFIGURACIÓN DE RED DEL SERVIDOR
# -----------------------------------------------------------------------------
# HOST: Definimos "0.0.0.0" como dirección de escucha (INADDR_ANY). Esto le indica
# al sistema operativo que el servidor debe aceptar conexiones entrantes desde todas
# las interfaces de red disponibles en la máquina (localhost 127.0.0.1 para pruebas
# locales en la misma máquina, y la dirección IP privada de la red Wi-Fi o Ethernet
# para permitir la conexión desde otras computadoras de la red local).
HOST = "0.0.0.0"

# PUERTO: Puerto de transporte TCP seleccionado para el servicio (5000).
# Es un puerto no privilegiado (mayor a 1024) adecuado para aplicaciones de usuario.
PUERTO = 5000

# Diccionario global para mantener el registro en memoria de los clientes conectados.
# Estructura: clave = nombre_de_usuario (str), valor = socket_de_conexion (socket.socket).
# Esto nos permite identificar a cada usuario activo y enviarle mensajes dirigidos o colectivos.
clientes_conectados = {}

# Variables globales para enlazar y manipular los componentes visuales de Tkinter desde
# cualquier función o hilo del programa.
area_logs = None
combo_destinatario = None
lbl_estado_clientes = None
lbl_estado_bd = None
lbl_info_ip = None
ventana_servidor = None
var_destinatario = None
entrada_mensaje_admin = None


# -----------------------------------------------------------------------------
# 3. FUNCIONES AUXILIARES DE RED Y REGISTRO EN PANTALLA
# -----------------------------------------------------------------------------
def obtener_ip_local():
    """
    Función auxiliar para determinar la dirección IP real de la máquina dentro
    de la red de área local (LAN / Wi-Fi).
    Crea un socket UDP provisional sin llegar a transmitir datos en la red;
    al conectarlo contra una IP pública de referencia (8.8.8.8 de Google),
    el sistema operativo asigna la interfaz de red activa y devuelve su IP local.
    Si no hay conexión externa disponible, devuelve por defecto '127.0.0.1'.
    """
    try:
        s_provisional = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_provisional.connect(("8.8.8.8", 80))
        ip_detectada = s_provisional.getsockname()[0]
        s_provisional.close()
        return ip_detectada
    except Exception:
        return "127.0.0.1"


def registrar_log(texto):
    """
    Muestra los mensajes y eventos tanto en la consola de texto estándar (terminal)
    como en el componente visual Text de la interfaz de usuario de Tkinter.
    Incluye una marca de tiempo con formato [HH:MM:SS] para auditoría de eventos.
    """
    hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
    mensaje_formateado = f"[{hora_actual}] {texto}"
    
    # Imprimimos en terminal para seguimiento técnico durante las pruebas
    print(mensaje_formateado)
    
    # Si la interfaz gráfica ya fue construida, insertamos el texto en el visor de logs
    if area_logs is not None:
        try:
            # Desbloqueamos temporalmente el área de texto para insertar nueva línea
            area_logs.config(state=tk.NORMAL)
            area_logs.insert(tk.END, mensaje_formateado + "\n")
            # Hacemos auto-scroll hacia el final para que el operador siempre vea el último evento
            area_logs.see(tk.END)
            # Volvemos a bloquear el componente para evitar que el usuario lo modifique accidentalmente
            area_logs.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Error al escribir en visor de logs de la interfaz: {e}")


def actualizar_lista_usuarios_gui():
    """
    Actualiza la etiqueta con la cantidad de usuarios activos y reconstruye
    dinámicamente las opciones del menú desplegable de destinatarios para
    permitir que el administrador seleccione a quién enviarle mensajes directos.
    """
    if lbl_estado_clientes is not None:
        cantidad = len(clientes_conectados)
        lbl_estado_clientes.config(text=f"Clientes conectados: {cantidad}")

    if combo_destinatario is not None:
        menu = combo_destinatario["menu"]
        menu.delete(0, "end")
        
        # Opción predeterminada para transmisión masiva (broadcast a todos los clientes)
        menu.add_command(label="TODOS", command=lambda: var_destinatario.set("TODOS"))
        
        # Agregamos cada usuario conectado individualmente como opción
        for usuario in list(clientes_conectados.keys()):
            menu.add_command(label=usuario, command=lambda u=usuario: var_destinatario.set(u))


def enviar_broadcast(mensaje):
    """
    Envía una cadena de texto codificada en bytes UTF-8 a todos los clientes
    conectados en ese momento.
    Iteramos sobre una copia de los items del diccionario para evitar errores si
    un cliente se desconecta durante el recorrido.
    """
    for usuario, sock_cliente in list(clientes_conectados.items()):
        try:
            sock_cliente.send(mensaje.encode("utf-8"))
        except Exception as error_envio:
            registrar_log(f"Error al emitir broadcast hacia '{usuario}': {error_envio}")


# -----------------------------------------------------------------------------
# 4. HILO INDEPENDIENTE PARA ATENCIÓN DE CADA CLIENTE (CONCURRENCIA)
# -----------------------------------------------------------------------------
def atender_cliente(conn, addr):
    """
    Función que ejecuta cada hilo dedicado a un cliente entrante (Punto 1 del TP).
    Parámetros:
      - conn: objeto socket de la conexión individual establecida.
      - addr: tupla (ip_cliente, puerto_cliente) con los datos del origen.
      
    Flujo de ejecución:
      1. Recibe y decodifica las credenciales en formato 'usuario|password'.
      2. Valida contra la base de datos MySQL (Punto 2 del TP).
      3. Si es erróneo, responde error y cierra el socket (Punto 3 del TP).
      4. Si es correcto, da la bienvenida e inicia el bucle de recepción.
      5. Discrimina mensajes de chat común o comandos con '/' (Puntos 4, 5 y 6).
      6. En la desconexión, libera los recursos y actualiza las listas.
    """
    usuario_actual = None
    ip_origen = addr[0]
    puerto_origen = addr[1]
    
    registrar_log(f"Nueva conexión TCP aceptada desde {ip_origen}:{puerto_origen}")

    try:
        # Paso 1: Esperamos el paquete inicial con las credenciales enviadas por el cliente
        datos_recibidos = conn.recv(1024).decode("utf-8").strip()
        
        # Verificamos que el paquete cumpla con el protocolo establecido: 'usuario|contraseña'
        if not datos_recibidos or "|" not in datos_recibidos:
            mensaje_error = "ERROR|Protocolo inválido. Se esperaba 'usuario|password'."
            conn.send(mensaje_error.encode("utf-8"))
            conn.close()
            registrar_log(f"Conexión rechazada desde {ip_origen}:{puerto_origen}: formato incorrecto.")
            return

        # Separamos usuario y contraseña
        partes_login = datos_recibidos.split("|", 1)
        username = partes_login[0].strip()
        password = partes_login[1].strip()

        # Paso 2: Validación de credenciales en la tabla 'usuarios' de MySQL (Punto 2 del TP)
        es_valido = validar_usuario(username, password)

        # Paso 3: Decisión según resultado de la autenticación (Punto 3 del TP)
        if not es_valido:
            registrar_log(f"Autenticación FALLIDA para usuario '{username}' desde {ip_origen}:{puerto_origen}")
            mensaje_error = "ERROR|Credenciales inválidas. Acceso denegado por el servidor."
            conn.send(mensaje_error.encode("utf-8"))
            conn.close()
            return

        # Verificamos si el usuario ya cuenta con una sesión abierta para evitar duplicados
        if username in clientes_conectados:
            registrar_log(f"Intento de sesión duplicada para '{username}' desde {ip_origen}:{puerto_origen}")
            mensaje_error = "ERROR|El usuario ya posee una sesión activa en el servidor."
            conn.send(mensaje_error.encode("utf-8"))
            conn.close()
            return

        # Si las credenciales son válidas, registramos al cliente en el diccionario global
        usuario_actual = username
        clientes_conectados[usuario_actual] = conn
        actualizar_lista_usuarios_gui()

        # Enviamos confirmación exitosa con mensaje de bienvenida (Punto 3 del TP)
        mensaje_ok = f"OK|¡Bienvenido al sistema {usuario_actual}! Conexión establecida exitosamente."
        conn.send(mensaje_ok.encode("utf-8"))
        registrar_log(f"Usuario '{usuario_actual}' autenticado correctamente desde {ip_origen}:{puerto_origen}")

        # Notificamos al resto de los clientes la conexión del nuevo usuario
        enviar_broadcast(f"[SISTEMA]: El usuario '{usuario_actual}' ha ingresado a la sala.")

        # ---------------------------------------------------------------------
        # Paso 4: Bucle principal de recepción de mensajes y comandos
        # ---------------------------------------------------------------------
        while True:
            # Bloquea la espera hasta recibir hasta 1024 bytes desde el socket del cliente
            paquete = conn.recv(1024)
            
            # Si recv() retorna bytes vacíos (b''), significa que el cliente cerró el socket
            if not paquete:
                registrar_log(f"Cliente '{usuario_actual}' desconectado de forma normal.")
                break

            mensaje = paquete.decode("utf-8").strip()
            if not mensaje:
                continue

            # -----------------------------------------------------------------
            # Paso 5: Procesamiento de comandos iniciados con "/" (Puntos 5 y 6)
            # -----------------------------------------------------------------
            if mensaje.startswith("/"):
                registrar_log(f"Comando recibido de '{usuario_actual}': {mensaje}")
                
                # Descomponemos el mensaje en comando y posible argumento
                partes_comando = mensaje.split(" ", 1)
                cmd = partes_comando[0].lower()
                argumento = partes_comando[1].strip() if len(partes_comando) > 1 else ""

                # -------------------------------------------------------------
                # Comando a: /repos usuario
                # Consulta la API de GitHub y guarda nombre y html_url en la BD
                # -------------------------------------------------------------
                if cmd == "/repos":
                    if not argumento:
                        conn.send("[SERVIDOR]: Sintaxis incorrecta. Uso: /repos <usuario_github>".encode("utf-8"))
                    else:
                        url_api = f"https://api.github.com/users/{argumento}/repos"
                        params = {"per_page": 30}
                        try:
                            # Realizamos petición GET HTTP a la API REST pública de GitHub
                            respuesta_http = requests.get(url_api, params=params, timeout=10)
                            
                            if respuesta_http.status_code == 200:
                                lista_repos = respuesta_http.json()
                                # Invocamos la función de persistencia en la tabla 'repositorios'
                                filas_insertadas = guardar_repositorios_bd(lista_repos)
                                respuesta_cliente = (
                                    f"[SERVIDOR]: Éxito. Se consultó la API de GitHub y se guardaron "
                                    f"{filas_insertadas} repositorios de '{argumento}' en la base de datos."
                                )
                                conn.send(respuesta_cliente.encode("utf-8"))
                                registrar_log(f"BD: {filas_insertadas} repositorios guardados para '{argumento}'.")
                            elif respuesta_http.status_code == 404:
                                conn.send(f"[SERVIDOR]: No se encontró el usuario de GitHub '{argumento}' (Error 404).".encode("utf-8"))
                            else:
                                conn.send(f"[SERVIDOR]: La API de GitHub respondió con código HTTP {respuesta_http.status_code}.".encode("utf-8"))
                        except requests.RequestException as error_http:
                            conn.send(f"[SERVIDOR]: Error de conexión al consultar la API de GitHub: {error_http}".encode("utf-8"))

                # -------------------------------------------------------------
                # Comando b: /followers usuario
                # Consulta la API de GitHub y guarda login y html_url en la BD
                # -------------------------------------------------------------
                elif cmd == "/followers":
                    if not argumento:
                        conn.send("[SERVIDOR]: Sintaxis incorrecta. Uso: /followers <usuario_github>".encode("utf-8"))
                    else:
                        url_api = f"https://api.github.com/users/{argumento}/followers"
                        params = {"per_page": 30}
                        try:
                            respuesta_http = requests.get(url_api, params=params, timeout=10)
                            if respuesta_http.status_code == 200:
                                lista_followers = respuesta_http.json()
                                filas_insertadas = guardar_followers_bd(lista_followers)
                                respuesta_cliente = (
                                    f"[SERVIDOR]: Éxito. Se consultó la API de GitHub y se guardaron "
                                    f"{filas_insertadas} seguidores de '{argumento}' en la base de datos."
                                )
                                conn.send(respuesta_cliente.encode("utf-8"))
                                registrar_log(f"BD: {filas_insertadas} followers guardados para '{argumento}'.")
                            elif respuesta_http.status_code == 404:
                                conn.send(f"[SERVIDOR]: No se encontró el usuario de GitHub '{argumento}' (Error 404).".encode("utf-8"))
                            else:
                                conn.send(f"[SERVIDOR]: La API de GitHub respondió con código HTTP {respuesta_http.status_code}.".encode("utf-8"))
                        except requests.RequestException as error_http:
                            conn.send(f"[SERVIDOR]: Error de conexión al consultar la API de GitHub: {error_http}".encode("utf-8"))

                # -------------------------------------------------------------
                # Comando c: /hora
                # Devuelve la hora actual del servidor en formato HH:MM:SS
                # -------------------------------------------------------------
                elif cmd == "/hora":
                    hora_actual_str = datetime.datetime.now().strftime("%H:%M:%S")
                    conn.send(f"[SERVIDOR]: La hora oficial del sistema es: {hora_actual_str}".encode("utf-8"))

                # -------------------------------------------------------------
                # Comando d: /todos "mensaje"
                # Reenvía el mensaje a todos los clientes conectados en la sala
                # -------------------------------------------------------------
                elif cmd == "/todos":
                    texto_limpio = argumento.strip('"').strip("'").strip()
                    if not texto_limpio:
                        conn.send('[SERVIDOR]: Sintaxis incorrecta. Uso: /todos "mensaje"'.encode("utf-8"))
                    else:
                        mensaje_broadcast = f"[DIFUSIÓN de {usuario_actual}]: {texto_limpio}"
                        registrar_log(mensaje_broadcast)
                        enviar_broadcast(mensaje_broadcast)

                # -------------------------------------------------------------
                # Comando e: /usuarios
                # Lista los nombres de los usuarios con sesión activa
                # -------------------------------------------------------------
                elif cmd == "/usuarios":
                    usuarios_activos = list(clientes_conectados.keys())
                    total = len(usuarios_activos)
                    nombres = ", ".join(usuarios_activos)
                    conn.send(f"[SERVIDOR]: Usuarios conectados ({total}): {nombres}".encode("utf-8"))

                # -------------------------------------------------------------
                # Comando f: /adios
                # Desconecta la sesión del cliente solicitante
                # -------------------------------------------------------------
                elif cmd == "/adios":
                    conn.send("[SERVIDOR]: Sesión finalizada correctamente. ¡Hasta luego!".encode("utf-8"))
                    registrar_log(f"El usuario '{usuario_actual}' solicitó desconexión con /adios.")
                    break

                # Caso comando no reconocido
                else:
                    conn.send(f"[SERVIDOR]: Comando '{cmd}' no válido. Comandos: /repos, /followers, /hora, /todos, /usuarios, /adios.".encode("utf-8"))

            else:
                # -------------------------------------------------------------
                # Paso 6: Mensaje de texto plano (chat cliente -> servidor) (Punto 4)
                # -------------------------------------------------------------
                registrar_log(f"[MENSAJE de {usuario_actual}]: {mensaje}")
                # Confirmamos al cliente que su mensaje fue recibido por el servidor
                conn.send(f"[Servidor recibió tu mensaje]: {mensaje}".encode("utf-8"))

    except ConnectionResetError:
        registrar_log(f"Conexión reseteada abruptamente por el cliente '{usuario_actual}'.")
    except Exception as error_general:
        registrar_log(f"Excepción en la atención del cliente '{usuario_actual}': {error_general}")
    finally:
        # Bloque de cierre y limpieza de recursos garantizado
        if usuario_actual and usuario_actual in clientes_conectados:
            del clientes_conectados[usuario_actual]
            actualizar_lista_usuarios_gui()
            enviar_broadcast(f"[SISTEMA]: El usuario '{usuario_actual}' se ha desconectado.")
        
        try:
            conn.close()
        except Exception:
            pass
        registrar_log(f"Socket cerrado para el origen {ip_origen}:{puerto_origen}")


# -----------------------------------------------------------------------------
# 5. HILO DE ESCUCHA DEL SOCKET SERVIDOR
# -----------------------------------------------------------------------------
def iniciar_socket_servidor():
    """
    Crea el socket TCP maestro, lo asocia a la IP y puerto especificados,
    y entra en un bucle infinito aceptando conexiones con accept().
    Por cada cliente que se suma, crea e inicia un nuevo hilo de ejecución (visto en el primer parcial).
    """
    try:
        # socket.AF_INET especifica la familia de protocolos IPv4.
        # socket.SOCK_STREAM define que usaremos el protocolo TCP (orientado a conexión, confiable).
        servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # SOL_SOCKET y SO_REUSEADDR permiten reutilizar la dirección local inmediatamente
        # después de reiniciar el servidor, evitando el bloqueo 'Address already in use' (TIME_WAIT).
        servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Enlazamos el socket a la dirección y puerto configurados
        servidor_socket.bind((HOST, PUERTO))
        
        # Habilitamos la cola de peticiones pendientes (backlog de 10)
        servidor_socket.listen(10)
        
        ip_lan = obtener_ip_local()
        registrar_log(f"Servidor TCP iniciado exitosamente en puerto {PUERTO}.")
        registrar_log(f"Escuchando en IP LAN: {ip_lan} | Localhost: 127.0.0.1")
        
        if lbl_info_ip is not None:
            lbl_info_ip.config(text=f"IP LAN: {ip_lan} | Puerto: {PUERTO}")

        # Verificación y conexión inicial con la base de datos MySQL (XAMPP)
        bd_operativa = inicializar_bd_si_no_existe()
        if bd_operativa:
            registrar_log("Conexión con base de datos MySQL 'db_github_api': OPERATIVA.")
            if lbl_estado_bd is not None:
                lbl_estado_bd.config(text="Base de Datos: MySQL Conectada (db_github_api)", fg="#2e7d32")
        else:
            registrar_log("ADVERTENCIA: No se pudo conectar a MySQL. Verifique que XAMPP esté iniciado.")
            if lbl_estado_bd is not None:
                lbl_estado_bd.config(text="Base de Datos: ERROR (MySQL no responde en puerto 3306)", fg="#c62828")

        # Bucle de aceptación de conexiones entrantes
        while True:
            # accept() bloquea hasta que arriba una nueva solicitud de conexión de un cliente
            socket_cliente, direccion_cliente = servidor_socket.accept()
            
            # Instanciamos un hilo por cliente asignándole la función 'atender_cliente'
            # daemon=True garantiza que si la aplicación principal finaliza, los hilos se destruyan
            hilo_cliente = threading.Thread(
                target=atender_cliente,
                args=(socket_cliente, direccion_cliente),
                daemon=True
            )
            hilo_cliente.start()

    except Exception as error_socket:
        registrar_log(f"Error crítico en el socket principal del servidor: {error_socket}")


# -----------------------------------------------------------------------------
# 6. ENVÍO DE MENSAJES DESDE EL PANEL DE ADMINISTRACIÓN DEL SERVIDOR
# -----------------------------------------------------------------------------
def enviar_mensaje_admin(event=None):
    """
    Función para que el operador del servidor pueda responder o emitir
    mensajes hacia los clientes (Punto 4 del TP: comunicación bidireccional).
    Permite enviar a 'TODOS' o a un usuario específico seleccionado en el desplegable.
    """
    contenido = entrada_mensaje_admin.get().strip()
    if not contenido:
        return

    destinatario = var_destinatario.get()

    if not clientes_conectados:
        messagebox.showwarning("Atención", "No hay clientes conectados actualmente.")
        return

    if destinatario == "TODOS":
        enviar_broadcast(f"[SERVIDOR -> TODOS]: {contenido}")
        registrar_log(f"Admin -> TODOS: {contenido}")
    else:
        if destinatario in clientes_conectados:
            try:
                clientes_conectados[destinatario].send(f"[SERVIDOR -> {destinatario}]: {contenido}".encode("utf-8"))
                registrar_log(f"Admin -> {destinatario}: {contenido}")
            except Exception as e:
                registrar_log(f"Error al enviar a '{destinatario}': {e}")
        else:
            messagebox.showwarning("Usuario no disponible", f"El cliente '{destinatario}' ya no está conectado.")
            var_destinatario.set("TODOS")

    # Limpiamos el campo de entrada luego del envío
    entrada_mensaje_admin.delete(0, tk.END)


def limpiar_consola_logs():
    """Limpia el área visual de registros en pantalla."""
    if area_logs is not None:
        area_logs.config(state=tk.NORMAL)
        area_logs.delete("1.0", tk.END)
        area_logs.config(state=tk.DISABLED)
        registrar_log("Consola de registros reiniciada por el operador.")


# -----------------------------------------------------------------------------
# 7. CONSTRUCCIÓN DE LA INTERFAZ GRÁFICA DE USUARIO (TKINTER)
# -----------------------------------------------------------------------------
ventana_servidor = tk.Tk()
ventana_servidor.title("Servidor Concurrente TCP - TP Final Programación sobre Redes (IFTS4)")
ventana_servidor.geometry("780x560")
ventana_servidor.minsize(680, 480)
ventana_servidor.configure(bg="#f4f6f9")

# --- Panel Superior: Encabezado y Estado del Sistema ---
frame_superior = tk.Frame(ventana_servidor, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=10)
frame_superior.pack(fill=tk.X, padx=10, pady=(10, 6))

lbl_titulo = tk.Label(
    frame_superior,
    text="PANEL DE CONTROL - SERVIDOR CONCURRENTE TCP",
    font=("Segoe UI", 12, "bold"),
    bg="#ffffff",
    fg="#1a237e"
)
lbl_titulo.pack(anchor="w")

frame_info_red = tk.Frame(frame_superior, bg="#ffffff")
frame_info_red.pack(fill=tk.X, pady=(4, 0))

lbl_info_ip = tk.Label(
    frame_info_red,
    text=f"IP LAN: {obtener_ip_local()} | Puerto: {PUERTO}",
    font=("Segoe UI", 9),
    bg="#ffffff",
    fg="#37474f"
)
lbl_info_ip.pack(side=tk.LEFT)

lbl_estado_clientes = tk.Label(
    frame_info_red,
    text="Clientes conectados: 0",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#0d47a1"
)
lbl_estado_clientes.pack(side=tk.RIGHT)

lbl_estado_bd = tk.Label(
    frame_superior,
    text="Base de Datos: Verificando conexión...",
    font=("Segoe UI", 9),
    bg="#ffffff",
    fg="#555555"
)
lbl_estado_bd.pack(anchor="w", pady=(2, 0))

# --- Panel Central: Consola de Registros y Actividad de Red ---
frame_central = tk.Frame(ventana_servidor, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=8)
frame_central.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

frame_cabecera_consola = tk.Frame(frame_central, bg="#ffffff")
frame_cabecera_consola.pack(fill=tk.X, pady=(0, 4))

tk.Label(
    frame_cabecera_consola,
    text="Registro de Actividad y Tráfico de Red (Sockets / BD / Comandos):",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#263238"
).pack(side=tk.LEFT)

btn_limpiar = tk.Button(
    frame_cabecera_consola,
    text="Limpiar pantalla",
    command=limpiar_consola_logs,
    font=("Segoe UI", 8),
    bg="#e0e0e0",
    relief=tk.GROOVE,
    padx=6
)
btn_limpiar.pack(side=tk.RIGHT)

# Componente Text con Scrollbar vertical para visualizar los eventos
scrollbar_logs = tk.Scrollbar(frame_central)
scrollbar_logs.pack(side=tk.RIGHT, fill=tk.Y)

area_logs = tk.Text(
    frame_central,
    wrap=tk.WORD,
    font=("Consolas", 9),
    bg="#1e1e1e",
    fg="#dcdcdc",
    insertbackground="white",
    yscrollcommand=scrollbar_logs.set,
    bd=0,
    padx=8,
    pady=6,
    state=tk.DISABLED
)
area_logs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_logs.config(command=area_logs.yview)

# --- Panel Inferior: Transmisión y Chat hacia los Clientes (Punto 4) ---
frame_inferior = tk.Frame(ventana_servidor, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=10)
frame_inferior.pack(fill=tk.X, padx=10, pady=(6, 10))

tk.Label(
    frame_inferior,
    text="Destinatario:",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#37474f"
).pack(side=tk.LEFT, padx=(0, 4))

var_destinatario = tk.StringVar(value="TODOS")
combo_destinatario = tk.OptionMenu(frame_inferior, var_destinatario, "TODOS")
combo_destinatario.config(font=("Segoe UI", 9), bg="#eceff1", width=12)
combo_destinatario.pack(side=tk.LEFT, padx=(0, 8))

entrada_mensaje_admin = tk.Entry(
    frame_inferior,
    font=("Segoe UI", 10),
    bd=1,
    relief=tk.SOLID
)
entrada_mensaje_admin.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
entrada_mensaje_admin.bind("<Return>", enviar_mensaje_admin)

btn_enviar_admin = tk.Button(
    frame_inferior,
    text="Enviar a Cliente(s)",
    command=enviar_mensaje_admin,
    bg="#1565c0",
    fg="#ffffff",
    font=("Segoe UI", 9, "bold"),
    activebackground="#0d47a1",
    activeforeground="#ffffff",
    relief=tk.RAISED,
    padx=12,
    pady=4,
    cursor="hand2"
)
btn_enviar_admin.pack(side=tk.RIGHT)

# -----------------------------------------------------------------------------
# 8. INICIO DEL SERVICIO
# -----------------------------------------------------------------------------
# Iniciamos el socket servidor en un hilo secundario independiente (daemon=True)
# para que no congele la ejecución del bucle principal de eventos de Tkinter (mainloop).
hilo_escucha = threading.Thread(target=iniciar_socket_servidor, daemon=True)
hilo_escucha.start()

# Iniciamos el bucle de eventos de la ventana gráfica de administración
ventana_servidor.mainloop()
