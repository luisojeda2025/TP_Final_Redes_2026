# =============================================================================
# INSTITUCIÓN: IFTS N° 4
# CARRERA: Tecnicatura Superior en Desarrollo de Software
# MATERIA: Programación sobre Redes
# PROFESOR: Javier Blanco
# ALUMNO: Luis Segundo Ojeda
# TRABAJO PRÁCTICO: Trabajo Práctico Integrador Final
# ARCHIVO: cliente.py
# DESCRIPCIÓN: 
#   Cliente gráfico implementado con sockets TCP en Python.
#   Permite establecer una conexión con el servidor concurrente, autenticarse
#   mediante usuario y contraseña validados contra MySQL, enviar y recibir
#   mensajes de texto en tiempo real, y ejecutar los comandos de red con "/".
# =============================================================================

# -----------------------------------------------------------------------------
# 1. IMPORTACIÓN DE MÓDULOS DE LA BIBLIOTECA ESTÁNDAR
# -----------------------------------------------------------------------------
# El módulo socket proporciona la interfaz de programación para redes TCP/IP.
import socket

# El módulo threading se utiliza para crear un hilo secundario de escucha.
# De esta manera, el cliente puede recibir mensajes asíncronos del servidor
# sin congelar la interfaz gráfica de usuario creada con Tkinter.
import threading

# El módulo datetime nos permite estampar la hora de recepción en los mensajes.
import datetime

# Biblioteca gráfica estándar de Python para la interfaz de usuario.
import tkinter as tk
from tkinter import messagebox

# -----------------------------------------------------------------------------
# 2. CONFIGURACIÓN Y VARIABLES GLOBALES
# -----------------------------------------------------------------------------
# Valores predeterminados de conexión
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PUERTO = 5000

# Variables de control del socket y estado de la sesión
socket_cliente = None
esta_conectado = False
usuario_autenticado = ""

# Referencias globales a los componentes visuales de Tkinter
ventana_cliente = None
area_mensajes = None
entrada_mensaje = None
btn_enviar = None
entry_ip = None
entry_puerto = None
entry_usuario = None
entry_password = None
btn_conectar = None
btn_desconectar = None
lbl_estado_conexion = None


# -----------------------------------------------------------------------------
# 3. FUNCIONES DE INTERFAZ Y MANIPULACIÓN DEL VISOR DE TEXTO
# -----------------------------------------------------------------------------
def agregar_al_visor(texto):
    """
    Agrega una línea de texto formateada al componente visual Text.
    Maneja el desbloqueo temporal del widget (state=NORMAL) y su posterior
    bloqueo (state=DISABLED) para evitar que el usuario altere el historial.
    """
    if area_mensajes is not None:
        hora = datetime.datetime.now().strftime("%H:%M:%S")
        area_mensajes.config(state=tk.NORMAL)
        area_mensajes.insert(tk.END, f"[{hora}] {texto}\n")
        # see(tk.END) garantiza que el visor se desplace siempre al último mensaje recibido
        area_mensajes.see(tk.END)
        area_mensajes.config(state=tk.DISABLED)


def actualizar_estado_interfaz(conectado):
    """
    Habilita o deshabilita los componentes visuales según si el cliente
    se encuentra conectado o desconectado del servidor.
    """
    if conectado:
        lbl_estado_conexion.config(
            text=f"ESTADO: Conectado como '{usuario_autenticado}'",
            fg="#2e7d32"
        )
        entry_ip.config(state=tk.DISABLED)
        entry_puerto.config(state=tk.DISABLED)
        entry_usuario.config(state=tk.DISABLED)
        entry_password.config(state=tk.DISABLED)
        btn_conectar.config(state=tk.DISABLED)
        btn_desconectar.config(state=tk.NORMAL)
        entrada_mensaje.config(state=tk.NORMAL)
        btn_enviar.config(state=tk.NORMAL)
        entrada_mensaje.focus()
    else:
        lbl_estado_conexion.config(
            text="ESTADO: Desconectado",
            fg="#c62828"
        )
        entry_ip.config(state=tk.NORMAL)
        entry_puerto.config(state=tk.NORMAL)
        entry_usuario.config(state=tk.NORMAL)
        entry_password.config(state=tk.NORMAL)
        btn_conectar.config(state=tk.NORMAL)
        btn_desconectar.config(state=tk.DISABLED)
        entrada_mensaje.config(state=tk.DISABLED)
        btn_enviar.config(state=tk.DISABLED)


# -----------------------------------------------------------------------------
# 4. HILO SECUNDARIO DE ESCUCHA ASÍNCRONA (RECEPCIÓN DE MENSAJES)
# -----------------------------------------------------------------------------
def recibir_mensajes_servidor():
    """
    Hilo de recepción en segundo plano. Permanece en un bucle escuchando
    las tramas que el servidor envía a través del socket.
    Se ejecuta de forma asíncrona respecto al mainloop de Tkinter.
    """
    global esta_conectado, socket_cliente

    while esta_conectado:
        try:
            # recv() bloquea el hilo secundario hasta la llegada de nuevos bytes
            buffer = socket_cliente.recv(2048)
            
            # Si el buffer llega vacío, el servidor cerró el extremo de la conexión
            if not buffer:
                agregar_al_visor("[SISTEMA]: El servidor ha cerrado la conexión.")
                break

            mensaje_recibido = buffer.decode("utf-8")
            agregar_al_visor(mensaje_recibido)

            # Si el mensaje recibido indica la finalización de sesión por /adios
            if "Sesión finalizada correctamente" in mensaje_recibido:
                break

        except ConnectionResetError:
            agregar_al_visor("[SISTEMA]: Se interrumpió la conexión con el servidor.")
            break
        except Exception as error_recepcion:
            # Si ya nos estábamos desconectando intencionalmente, no mostramos error
            if esta_conectado:
                agregar_al_visor(f"[ERROR]: Excepción en recepción: {error_recepcion}")
            break

    # Si sale del bucle, procedemos al cierre limpio de la sesión local
    desconectar_del_servidor(notificar_servidor=False)


# -----------------------------------------------------------------------------
# 5. CONEXIÓN, AUTENTICACIÓN Y DESCONEXIÓN (PUNTOS 1, 2 Y 3 DEL TP)
# -----------------------------------------------------------------------------
def conectar_al_servidor(event=None):
    """
    Valida las entradas de conexión ingresadas por el usuario,
    instancia el socket TCP cliente, se conecta a la dirección del servidor,
    envía las credenciales y procesa la respuesta de login del servidor.
    """
    global socket_cliente, esta_conectado, usuario_autenticado

    # Obtenemos los valores desde los campos de entrada
    ip_servidor = entry_ip.get().strip()
    puerto_texto = entry_puerto.get().strip()
    username = entry_usuario.get().strip()
    password = entry_password.get().strip()

    # Validamos que ningún campo esté en blanco (jajaja...chiste por su apellido profesor)
    if not ip_servidor or not puerto_texto or not username or not password:
        messagebox.showwarning("Campos incompletos", "Por favor complete IP, Puerto, Usuario y Contraseña.")
        return

    try:
        puerto_numero = int(puerto_texto)
    except ValueError:
        messagebox.showerror("Puerto inválido", "El puerto debe ser un número entero válido (por ejemplo 5000).")
        return

    try:
        # Paso 1: Creación del socket TCP (AF_INET = IPv4, SOCK_STREAM = TCP)
        socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Conectamos con el endpoint remoto (IP, Puerto)
        socket_cliente.connect((ip_servidor, puerto_numero))

        # Paso 2: Envío de credenciales según el protocolo: 'usuario|password'
        paquete_autenticacion = f"{username}|{password}"
        socket_cliente.send(paquete_autenticacion.encode("utf-8"))

        # Paso 3: Esperamos la respuesta de autenticación del servidor (Punto 3 del TP)
        respuesta_servidor = socket_cliente.recv(1024).decode("utf-8")

        # Discriminamos el resultado de la validación
        if respuesta_servidor.startswith("OK|"):
            # Login exitoso
            mensaje_bienvenida = respuesta_servidor.split("|", 1)[1]
            usuario_autenticado = username
            esta_conectado = True
            
            actualizar_estado_interfaz(True)
            agregar_al_visor(f"[AUTENTICACIÓN]: {mensaje_bienvenida}")
            
            # Lanzamos el hilo que quedará escuchando las respuestas y mensajes en segundo plano
            hilo_escucha = threading.Thread(target=recibir_mensajes_servidor, daemon=True)
            hilo_escucha.start()

        elif respuesta_servidor.startswith("ERROR|"):
            # Login fallido o rechazado
            motivo_error = respuesta_servidor.split("|", 1)[1]
            socket_cliente.close()
            socket_cliente = None
            actualizar_estado_interfaz(False)
            messagebox.showerror("Error de Autenticación", motivo_error)
            agregar_al_visor(f"[AUTENTICACIÓN RECHAZADA]: {motivo_error}")

        else:
            # Respuesta inesperada
            socket_cliente.close()
            socket_cliente = None
            actualizar_estado_interfaz(False)
            messagebox.showerror("Error de Protocolo", f"Respuesta no reconocida: {respuesta_servidor}")

    except ConnectionRefusedError:
        actualizar_estado_interfaz(False)
        messagebox.showerror(
            "Conexión rechazada",
            f"No se pudo establecer conexión con {ip_servidor}:{puerto_numero}.\n"
            "Verifique que 'servidor.py' se encuentre en ejecución y escuchando en ese puerto."
        )
    except Exception as error_conexion:
        actualizar_estado_interfaz(False)
        messagebox.showerror("Error de Red", f"Ocurrió un error al conectar: {error_conexion}")


def desconectar_del_servidor(notificar_servidor=True):
    """
    Cierra la conexión TCP con el servidor y restaura el estado de los controles.
    Si notificar_servidor es True, envía previamente el comando /adios.
    """
    global socket_cliente, esta_conectado, usuario_autenticado

    if not esta_conectado and socket_cliente is None:
        return

    esta_conectado = False

    if socket_cliente is not None:
        if notificar_servidor:
            try:
                # Enviamos el comando formal de despedida /adios
                socket_cliente.send("/adios".encode("utf-8"))
            except Exception:
                pass
        try:
            socket_cliente.close()
        except Exception:
            pass
        socket_cliente = None

    usuario_autenticado = ""
    actualizar_estado_interfaz(False)
    agregar_al_visor("[SISTEMA]: Sesión desconectada.")


# -----------------------------------------------------------------------------
# 6. ENVÍO DE MENSAJES Y COMANDOS (PUNTOS 4, 5 Y 6 DEL TP)
# -----------------------------------------------------------------------------
def enviar_mensaje(event=None):
    """
    Toma el texto escrito por el usuario en el campo inferior,
    lo codifica en UTF-8 y lo transmite a través del socket TCP.
    Acepta tanto texto ordinario de conversación como comandos que inician con '/'.
    """
    if not esta_conectado or socket_cliente is None:
        messagebox.showwarning("Che!!! Sin conexión...", "Debes iniciar sesión antes de transmitir mensajes.")
        return

    texto = entrada_mensaje.get().strip()
    if not texto:
        return

    try:
        # Transmitimos la cadena de texto por el socket
        socket_cliente.send(texto.encode("utf-8"))
        
        # Limpiamos el campo de entrada y volvemos a posicionar el cursor
        entrada_mensaje.delete(0, tk.END)
        entrada_mensaje.focus()

    except Exception as error_envio:
        agregar_al_visor(f"[ERROR DE ENVÍO]: {error_envio}")


def al_cerrar_ventana():
    """
    Manejador del evento WM_DELETE_WINDOW (al pulsar la 'X' de la ventana).
    Garantiza que la conexión se despida limpiamente antes de destruir la GUI.
    """
    desconectar_del_servidor(notificar_servidor=True)
    ventana_cliente.destroy()


# -----------------------------------------------------------------------------
# 7. CONSTRUCCIÓN DE LA INTERFAZ GRÁFICA DE USUARIO (TKINTER)
# -----------------------------------------------------------------------------
ventana_cliente = tk.Tk()
ventana_cliente.title("Cliente TCP - TP Final Programación sobre Redes (IFTS4)")
ventana_cliente.geometry("680x540")
ventana_cliente.minsize(600, 460)
ventana_cliente.configure(bg="#f4f6f9")

# --- Panel Superior: Configuración de Conexión y Autenticación (Puntos 1, 2 y 3) ---
frame_login = tk.LabelFrame(
    ventana_cliente,
    text=" Panel de Conexión y Autenticación ",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#1a237e",
    bd=1,
    relief=tk.SOLID,
    padx=10,
    pady=8
)
frame_login.pack(fill=tk.X, padx=10, pady=(10, 6))

# Fila 1: Dirección IP y Puerto del Servidor
fila_red = tk.Frame(frame_login, bg="#ffffff")
fila_red.pack(fill=tk.X, pady=2)

tk.Label(fila_red, text="IP Servidor:", font=("Segoe UI", 9), bg="#ffffff", width=12, anchor="w").pack(side=tk.LEFT)
entry_ip = tk.Entry(fila_red, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=16)
entry_ip.insert(0, DEFAULT_HOST)
entry_ip.pack(side=tk.LEFT, padx=(0, 15))

tk.Label(fila_red, text="Puerto:", font=("Segoe UI", 9), bg="#ffffff", width=8, anchor="w").pack(side=tk.LEFT)
entry_puerto = tk.Entry(fila_red, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=8)
entry_puerto.insert(0, str(DEFAULT_PUERTO))
entry_puerto.pack(side=tk.LEFT)

# Fila 2: Usuario y Contraseña (validación en MySQL)
fila_credenciales = tk.Frame(frame_login, bg="#ffffff")
fila_credenciales.pack(fill=tk.X, pady=4)

tk.Label(fila_credenciales, text="Usuario:", font=("Segoe UI", 9), bg="#ffffff", width=12, anchor="w").pack(side=tk.LEFT)
entry_usuario = tk.Entry(fila_credenciales, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, width=16)
entry_usuario.insert(0, "alumno")
entry_usuario.pack(side=tk.LEFT, padx=(0, 15))

tk.Label(fila_credenciales, text="Contraseña:", font=("Segoe UI", 9), bg="#ffffff", width=8, anchor="w").pack(side=tk.LEFT)
entry_password = tk.Entry(fila_credenciales, font=("Segoe UI", 9), show="*", bd=1, relief=tk.SOLID, width=12)
entry_password.insert(0, "1234")
entry_password.pack(side=tk.LEFT)
entry_password.bind("<Return>", conectar_al_servidor)

# Fila 3: Botones de Conectar/Desconectar y Etiqueta de Estado
fila_botones_auth = tk.Frame(frame_login, bg="#ffffff")
fila_botones_auth.pack(fill=tk.X, pady=(6, 2))

btn_conectar = tk.Button(
    fila_botones_auth,
    text="Conectar / Iniciar Sesión",
    command=conectar_al_servidor,
    bg="#2e7d32",
    fg="#ffffff",
    font=("Segoe UI", 9, "bold"),
    activebackground="#1b5e20",
    activeforeground="#ffffff",
    padx=10,
    cursor="hand2"
)
btn_conectar.pack(side=tk.LEFT, padx=(0, 8))

btn_desconectar = tk.Button(
    fila_botones_auth,
    text="Desconectar",
    command=lambda: desconectar_del_servidor(notificar_servidor=True),
    bg="#c62828",
    fg="#ffffff",
    font=("Segoe UI", 9),
    activebackground="#b71c1c",
    activeforeground="#ffffff",
    padx=10,
    state=tk.DISABLED,
    cursor="hand2"
)
btn_desconectar.pack(side=tk.LEFT, padx=(0, 15))

lbl_estado_conexion = tk.Label(
    fila_botones_auth,
    text="ESTADO: Desconectado",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#c62828"
)
lbl_estado_conexion.pack(side=tk.LEFT)

# --- Panel Central: Área de Conversación y Respuestas de Comandos ---
frame_chat = tk.LabelFrame(
    ventana_cliente,
    text=" Historial de Comunicación y Salida de Comandos ",
    font=("Segoe UI", 9, "bold"),
    bg="#ffffff",
    fg="#263238",
    bd=1,
    relief=tk.SOLID,
    padx=8,
    pady=6
)
frame_chat.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

scrollbar_chat = tk.Scrollbar(frame_chat)
scrollbar_chat.pack(side=tk.RIGHT, fill=tk.Y)

area_mensajes = tk.Text(
    frame_chat,
    wrap=tk.WORD,
    font=("Consolas", 9),
    bg="#fafafa",
    fg="#212121",
    insertbackground="black",
    yscrollcommand=scrollbar_chat.set,
    bd=0,
    state=tk.DISABLED
)
area_mensajes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_chat.config(command=area_mensajes.yview)

# --- Panel Inferior: Entrada de Texto y Comandos ---
frame_entrada = tk.Frame(ventana_cliente, bg="#ffffff", bd=1, relief=tk.SOLID, padx=10, pady=8)
frame_entrada.pack(fill=tk.X, padx=10, pady=(4, 10))

fila_input = tk.Frame(frame_entrada, bg="#ffffff")
fila_input.pack(fill=tk.X, pady=(0, 6))

entrada_mensaje = tk.Entry(
    fila_input,
    font=("Segoe UI", 10),
    bd=1,
    relief=tk.SOLID,
    state=tk.DISABLED
)
entrada_mensaje.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 8))
entrada_mensaje.bind("<Return>", enviar_mensaje)

btn_enviar = tk.Button(
    fila_input,
    text="Enviar Mensaje",
    command=enviar_mensaje,
    bg="#1565c0",
    fg="#ffffff",
    font=("Segoe UI", 9, "bold"),
    activebackground="#0d47a1",
    activeforeground="#ffffff",
    padx=12,
    pady=4,
    state=tk.DISABLED,
    cursor="hand2"
)
btn_enviar.pack(side=tk.RIGHT)

# Vinculamos el cierre de ventana al manejador seguro
ventana_cliente.protocol("WM_DELETE_WINDOW", al_cerrar_ventana)

# -----------------------------------------------------------------------------
# 8. INICIO DEL BUCLE DE EVENTOS DE TKINTER
# -----------------------------------------------------------------------------
ventana_cliente.mainloop()
